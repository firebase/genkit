/*
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

package com.google.genkit.plugins.localvec;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.genkit.ai.*;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;

/**
 * Local file-based document store implementation.
 * 
 * <p>
 * Stores documents and their embeddings in a JSON file for simple similarity
 * search. Uses cosine similarity for retrieval.
 */
public class LocalVecDocStore {

  private static final Logger logger = LoggerFactory.getLogger(LocalVecDocStore.class);
  private static final ObjectMapper objectMapper = new ObjectMapper();

  private final LocalVecConfig config;
  private final Map<String, DbValue> data;

  /**
   * Creates a new LocalVecDocStore.
   *
   * @param config
   *            the configuration
   */
  public LocalVecDocStore(LocalVecConfig config) {
    this.config = config;
    this.data = new ConcurrentHashMap<>();
    loadFromFile();
  }

  /**
   * Loads data from the file if it exists.
   */
  private void loadFromFile() {
    Path filePath = config.getFilePath();
    if (Files.exists(filePath)) {
      try {
        String content = Files.readString(filePath);
        Map<String, DbValue> loaded = objectMapper.readValue(content,
            new TypeReference<Map<String, DbValue>>() {
            });
        if (loaded != null) {
          data.putAll(loaded);
          logger.info("Loaded {} documents from {}", data.size(), filePath);
        }
      } catch (IOException e) {
        logger.warn("Failed to load data from {}: {}", filePath, e.getMessage());
      }
    }
  }

  /**
   * Saves data to the file.
   */
  private synchronized void saveToFile() {
    try {
      Path directory = config.getDirectory();
      if (!Files.exists(directory)) {
        Files.createDirectories(directory);
      }
      Path filePath = config.getFilePath();
      String json = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(data);
      Files.writeString(filePath, json);
      logger.debug("Saved {} documents to {}", data.size(), filePath);
    } catch (IOException e) {
      throw new GenkitException("Failed to save data to file", e);
    }
  }

  /**
   * Indexes documents with their embeddings.
   *
   * @param ctx
   *            the action context
   * @param documents
   *            the documents to index
   * @throws GenkitException
   *             if indexing fails
   */
  public void index(ActionContext ctx, List<Document> documents) throws GenkitException {
    if (documents == null || documents.isEmpty()) {
      return;
    }

    try {
      // Get embeddings for all documents
      EmbedRequest embedRequest = new EmbedRequest(documents);
      EmbedResponse embedResponse = config.getEmbedder().run(ctx, embedRequest);

      List<EmbedResponse.Embedding> embeddings = embedResponse.getEmbeddings();
      if (embeddings.size() != documents.size()) {
        throw new GenkitException(
            "Embedding count mismatch: expected " + documents.size() + ", got " + embeddings.size());
      }

      // Store each document with its embedding
      for (int i = 0; i < documents.size(); i++) {
        Document doc = documents.get(i);
        List<Float> embedding = floatArrayToList(embeddings.get(i).getValues());

        String id = computeDocumentId(doc);
        if (!data.containsKey(id)) {
          data.put(id, new DbValue(doc, embedding));
          logger.debug("Indexed document: {}", id);
        } else {
          logger.debug("Skipping duplicate document: {}", id);
        }
      }

      saveToFile();
      logger.info("Indexed {} documents to {}", documents.size(), config.getIndexName());

    } catch (Exception e) {
      throw new GenkitException("Failed to index documents: " + e.getMessage(), e);
    }
  }

  /**
   * Retrieves documents similar to the query.
   *
   * @param ctx
   *            the action context
   * @param request
   *            the retriever request
   * @return the retriever response with matched documents
   * @throws GenkitException
   *             if retrieval fails
   */
  public RetrieverResponse retrieve(ActionContext ctx, RetrieverRequest request) throws GenkitException {
    try {
      // Get query document
      Document queryDoc = request.getQuery();
      if (queryDoc == null) {
        throw new GenkitException("Query document is required");
      }

      // Get embedding for the query
      EmbedRequest embedRequest = new EmbedRequest(List.of(queryDoc));
      EmbedResponse embedResponse = config.getEmbedder().run(ctx, embedRequest);
      List<Float> queryEmbedding = floatArrayToList(embedResponse.getEmbeddings().get(0).getValues());

      // Get k parameter from options
      int k = 3;
      if (request.getOptions() != null) {
        Object optionsObj = request.getOptions();
        if (optionsObj instanceof Map) {
          @SuppressWarnings("unchecked")
          Map<String, Object> options = (Map<String, Object>) optionsObj;
          if (options.containsKey("k")) {
            k = ((Number) options.get("k")).intValue();
          }
        } else if (optionsObj instanceof RetrieverOptions) {
          k = ((RetrieverOptions) optionsObj).getK();
        }
      }

      // Score all documents by similarity
      List<ScoredDocument> scoredDocs = new ArrayList<>();
      for (DbValue dbValue : data.values()) {
        double score = cosineSimilarity(queryEmbedding, dbValue.getEmbedding());
        scoredDocs.add(new ScoredDocument(score, dbValue.getDoc()));
      }

      // Sort by score descending
      scoredDocs.sort((a, b) -> Double.compare(b.score, a.score));

      // Return top k documents
      List<Document> results = new ArrayList<>();
      for (int i = 0; i < Math.min(k, scoredDocs.size()); i++) {
        results.add(scoredDocs.get(i).doc);
      }

      logger.debug("Retrieved {} documents for query", results.size());
      return new RetrieverResponse(results);

    } catch (Exception e) {
      throw new GenkitException("Failed to retrieve documents: " + e.getMessage(), e);
    }
  }

  /**
   * Computes the MD5 hash of a document for deduplication.
   */
  private String computeDocumentId(Document doc) {
    try {
      MessageDigest md = MessageDigest.getInstance("MD5");
      String content = objectMapper.writeValueAsString(doc);
      byte[] digest = md.digest(content.getBytes());
      StringBuilder sb = new StringBuilder();
      for (byte b : digest) {
        sb.append(String.format("%02x", b));
      }
      return sb.toString();
    } catch (NoSuchAlgorithmException | IOException e) {
      throw new GenkitException("Failed to compute document ID", e);
    }
  }

  /**
   * Converts a float array to a List of Float.
   */
  private List<Float> floatArrayToList(float[] arr) {
    List<Float> list = new ArrayList<>(arr.length);
    for (float f : arr) {
      list.add(f);
    }
    return list;
  }

  /**
   * Computes cosine similarity between two vectors.
   */
  private double cosineSimilarity(List<Float> vec1, List<Float> vec2) {
    if (vec1.size() != vec2.size()) {
      throw new IllegalArgumentException("Vectors must have same length");
    }

    double dotProduct = 0.0;
    double norm1 = 0.0;
    double norm2 = 0.0;

    for (int i = 0; i < vec1.size(); i++) {
      float v1 = vec1.get(i);
      float v2 = vec2.get(i);
      dotProduct += v1 * v2;
      norm1 += v1 * v1;
      norm2 += v2 * v2;
    }

    double denominator = Math.sqrt(norm1) * Math.sqrt(norm2);
    if (denominator == 0) {
      return 0.0;
    }

    return dotProduct / denominator;
  }

  /**
   * Creates a retriever action for this document store.
   *
   * @return the retriever
   */
  public Retriever createRetriever() {
    String name = LocalVecPlugin.PROVIDER + "/" + config.getIndexName();
    return Retriever.builder().name(name).handler((ctx, request) -> retrieve(ctx, request)).build();
  }

  /**
   * Creates an indexer action for this document store.
   *
   * @return the indexer
   */
  public Indexer createIndexer() {
    String name = LocalVecPlugin.PROVIDER + "/" + config.getIndexName();
    return Indexer.builder().name(name).handler((ctx, request) -> {
      index(ctx, request.getDocuments());
      return new IndexerResponse();
    }).build();
  }

  /**
   * Gets the number of documents in the store.
   *
   * @return the document count
   */
  public int size() {
    return data.size();
  }

  /**
   * Clears all documents from the store.
   */
  public void clear() {
    data.clear();
    saveToFile();
  }

  /**
   * Internal class for scoring documents.
   */
  private static class ScoredDocument {
    final double score;
    final Document doc;

    ScoredDocument(double score, Document doc) {
      this.score = score;
      this.doc = doc;
    }
  }
}
