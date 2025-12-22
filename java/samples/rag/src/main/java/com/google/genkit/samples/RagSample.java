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

package com.google.genkit.samples;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.*;
import com.google.genkit.core.Flow;
import com.google.genkit.plugins.jetty.JettyPlugin;
import com.google.genkit.plugins.jetty.JettyPluginOptions;
import com.google.genkit.plugins.localvec.LocalVecConfig;
import com.google.genkit.plugins.localvec.LocalVecPlugin;
import com.google.genkit.plugins.openai.OpenAIPlugin;

/**
 * Sample application demonstrating RAG (Retrieval Augmented Generation) with
 * Genkit Java.
 *
 * <p>
 * This example shows how to:
 * <ul>
 * <li>Use the local vector store plugin for development</li>
 * <li>Index documents from text files</li>
 * <li>Create retriever flows to fetch relevant documents</li>
 * <li>Build RAG flows that combine retrieval with generation</li>
 * </ul>
 *
 * <p>
 * To run:
 * <ol>
 * <li>Set the OPENAI_API_KEY environment variable</li>
 * <li>Run: mvn exec:java</li>
 * </ol>
 */
public class RagSample {

  private static final Logger logger = LoggerFactory.getLogger(RagSample.class);

  /**
   * System prompt for RAG queries. Documents are automatically injected via the
   * .docs() option.
   */
  private static final String RAG_SYSTEM_PROMPT = """
      You are a helpful assistant that answers questions based on the provided context documents.

      Please provide a helpful answer based only on the context provided. If the context doesn't contain
      enough information to answer the question, say so.
      """;

  public static void main(String[] args) throws Exception {
    // Configure local vector stores with embedder name (will be resolved during
    // init)
    Path storageDir = Paths.get(System.getProperty("java.io.tmpdir"), "genkit-rag-sample");

    LocalVecConfig worldCapitalsConfig = LocalVecConfig.builder().indexName("world-capitals")
        .embedderName("openai/text-embedding-3-small").directory(storageDir).build();

    LocalVecConfig dogBreedsConfig = LocalVecConfig.builder().indexName("dog-breeds")
        .embedderName("openai/text-embedding-3-small").directory(storageDir).build();

    LocalVecConfig coffeeFactsConfig = LocalVecConfig.builder().indexName("coffee-facts")
        .embedderName("openai/text-embedding-3-small").directory(storageDir).build();

    // Create the Jetty server plugin
    JettyPlugin jetty = new JettyPlugin(JettyPluginOptions.builder().port(8080).build());

    // Create Genkit with all plugins - LocalVec embedders are resolved
    // automatically
    Genkit genkit = Genkit.builder().options(GenkitOptions.builder().devMode(true).reflectionPort(3100).build())
        .plugin(OpenAIPlugin.create()).plugin(LocalVecPlugin.builder().addStore(worldCapitalsConfig)
            .addStore(dogBreedsConfig).addStore(coffeeFactsConfig).build())
        .plugin(jetty).build();

    // Define flow to index world capitals data
    Flow<Void, String, Void> indexWorldCapitalsFlow = genkit.defineFlow("indexWorldCapitals", Void.class,
        String.class, (ctx, input) -> {
          List<Document> documents = loadDocumentsFromResource("/data/world-capitals.txt");
          genkit.index("devLocalVectorStore/world-capitals", documents);
          return "Indexed " + documents.size() + " world capitals documents";
        });

    // Define flow to index dog breeds data
    Flow<Void, String, Void> indexDogBreedsFlow = genkit.defineFlow("indexDogBreeds", Void.class, String.class,
        (ctx, input) -> {
          List<Document> documents = loadDocumentsFromResource("/data/dog-breeds.txt");
          genkit.index("devLocalVectorStore/dog-breeds", documents);
          return "Indexed " + documents.size() + " dog breeds documents";
        });

    // Define flow to index coffee facts data
    Flow<Void, String, Void> indexCoffeeFactsFlow = genkit.defineFlow("indexCoffeeFacts", Void.class, String.class,
        (ctx, input) -> {
          List<Document> documents = loadDocumentsFromResource("/data/coffee-facts.txt");
          genkit.index("devLocalVectorStore/coffee-facts", documents);
          return "Indexed " + documents.size() + " coffee facts documents";
        });

    // Define RAG flow for world capitals
    Flow<String, String, Void> askAboutCapitalsFlow = genkit.defineFlow("askAboutCapitals", String.class,
        String.class, (ctx, question) -> {
          // Retrieve relevant documents
          List<Document> docs = genkit.retrieve("devLocalVectorStore/world-capitals", question);

          // Generate answer with retrieved documents as context
          ModelResponse modelResponse = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
              .system(RAG_SYSTEM_PROMPT).prompt(question).docs(docs)
              .config(GenerationConfig.builder().temperature(0.3).build()).build());

          return modelResponse.getText();
        });

    // Define RAG flow for dog breeds
    Flow<String, String, Void> askAboutDogsFlow = genkit.defineFlow("askAboutDogs", String.class, String.class,
        (ctx, question) -> {
          List<Document> docs = genkit.retrieve("devLocalVectorStore/dog-breeds", question);

          ModelResponse modelResponse = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
              .system(RAG_SYSTEM_PROMPT).prompt(question).docs(docs)
              .config(GenerationConfig.builder().temperature(0.3).build()).build());

          return modelResponse.getText();
        });

    // Define RAG flow for coffee facts
    Flow<String, String, Void> askAboutCoffeeFlow = genkit.defineFlow("askAboutCoffee", String.class, String.class,
        (ctx, question) -> {
          List<Document> docs = genkit.retrieve("devLocalVectorStore/coffee-facts", question);

          ModelResponse modelResponse = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
              .system(RAG_SYSTEM_PROMPT).prompt(question).docs(docs)
              .config(GenerationConfig.builder().temperature(0.3).build()).build());

          return modelResponse.getText();
        });

    // Define a generic indexing flow that accepts documents
    Flow<List<String>, String, Void> indexDocumentsFlow = genkit.defineFlow("indexDocuments",
        (Class<List<String>>) (Class<?>) List.class, String.class, (ctx, texts) -> {
          List<Document> documents = texts.stream().map(Document::fromText).collect(Collectors.toList());

          genkit.index("devLocalVectorStore/world-capitals", documents);
          return "Indexed " + documents.size() + " documents";
        });

    // Define a simple retrieval-only flow
    Flow<Map, List<String>, Void> retrieveDocumentsFlow = genkit.defineFlow("retrieveDocuments", Map.class,
        (Class<List<String>>) (Class<?>) List.class, (ctx, input) -> {
          String query = (String) input.get("query");
          String store = (String) input.getOrDefault("store", "world-capitals");

          List<Document> docs = genkit.retrieve("devLocalVectorStore/" + store, query);

          return docs.stream().map(Document::text).collect(Collectors.toList());
        });

    logger.info("=".repeat(60));
    logger.info("Genkit RAG Sample Started");
    logger.info("=".repeat(60));
    logger.info("");
    logger.info("Available flows:");
    logger.info("");
    logger.info("Indexing flows (run these first to populate the vector stores):");
    logger.info("  - indexWorldCapitals: Index world capitals data");
    logger.info("  - indexDogBreeds: Index dog breeds data");
    logger.info("  - indexCoffeeFacts: Index coffee facts data");
    logger.info("  - indexDocuments: Index custom documents");
    logger.info("");
    logger.info("RAG Query flows:");
    logger.info("  - askAboutCapitals: Ask questions about world capitals");
    logger.info("  - askAboutDogs: Ask questions about dog breeds");
    logger.info("  - askAboutCoffee: Ask questions about coffee");
    logger.info("");
    logger.info("Retrieval flow:");
    logger.info("  - retrieveDocuments: Retrieve documents without generation");
    logger.info("");
    logger.info("Example calls:");
    logger.info("");
    logger.info("1. First, index the data:");
    logger.info("   curl -X POST http://localhost:8080/indexWorldCapitals");
    logger.info("   curl -X POST http://localhost:8080/indexDogBreeds");
    logger.info("   curl -X POST http://localhost:8080/indexCoffeeFacts");
    logger.info("");
    logger.info("2. Then query:");
    logger.info("   curl -X POST http://localhost:8080/askAboutCapitals \\");
    logger.info("     -H 'Content-Type: application/json' \\");
    logger.info("     -d '\"What is the capital of France?\"'");
    logger.info("");
    logger.info("   curl -X POST http://localhost:8080/askAboutDogs \\");
    logger.info("     -H 'Content-Type: application/json' \\");
    logger.info("     -d '\"What are good family dogs?\"'");
    logger.info("");
    logger.info("   curl -X POST http://localhost:8080/askAboutCoffee \\");
    logger.info("     -H 'Content-Type: application/json' \\");
    logger.info("     -d '\"How is espresso made?\"'");
    logger.info("");
    logger.info("3. Retrieve without generation:");
    logger.info("   curl -X POST http://localhost:8080/retrieveDocuments \\");
    logger.info("     -H 'Content-Type: application/json' \\");
    logger.info("     -d '{\"query\":\"France\",\"store\":\"world-capitals\",\"k\":2}'");
    logger.info("");
    logger.info("Reflection API: http://localhost:3100");
    logger.info("HTTP API: http://localhost:8080");
    logger.info("=".repeat(60));

    // Start the server and block - keeps the application running
    jetty.start();
  }

  /**
   * Loads documents from a text resource file. Each paragraph (separated by blank
   * lines) becomes a separate document.
   */
  private static List<Document> loadDocumentsFromResource(String resourcePath) {
    List<Document> documents = new ArrayList<>();

    try (InputStream is = RagSample.class.getResourceAsStream(resourcePath)) {
      if (is == null) {
        throw new RuntimeException("Resource not found: " + resourcePath);
      }

      BufferedReader reader = new BufferedReader(new InputStreamReader(is));
      StringBuilder paragraph = new StringBuilder();
      String line;

      while ((line = reader.readLine()) != null) {
        if (line.trim().isEmpty()) {
          if (paragraph.length() > 0) {
            documents.add(Document.fromText(paragraph.toString().trim()));
            paragraph = new StringBuilder();
          }
        } else {
          if (paragraph.length() > 0) {
            paragraph.append(" ");
          }
          paragraph.append(line.trim());
        }
      }

      // Don't forget the last paragraph
      if (paragraph.length() > 0) {
        documents.add(Document.fromText(paragraph.toString().trim()));
      }

    } catch (Exception e) {
      throw new RuntimeException("Failed to load documents from " + resourcePath, e);
    }

    logger.info("Loaded {} documents from {}", documents.size(), resourcePath);
    return documents;
  }
}
