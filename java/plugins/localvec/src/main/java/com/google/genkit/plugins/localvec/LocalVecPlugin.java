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

import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.ai.*;
import com.google.genkit.core.Action;
import com.google.genkit.core.ActionType;
import com.google.genkit.core.Plugin;
import com.google.genkit.core.Registry;

/**
 * Local file-based vector store plugin for development and testing.
 * 
 * <p>
 * This plugin provides a simple file-based vector store implementation suitable
 * for local development and testing. It stores document embeddings in JSON
 * files and performs similarity search using cosine similarity.
 * 
 * <p>
 * <b>NOT INTENDED FOR PRODUCTION USE.</b>
 * 
 * <p>
 * Example usage with embedder name (recommended):
 * 
 * <pre>{@code
 * Genkit genkit = Genkit.builder().plugin(OpenAIPlugin.create())
 * 		.plugin(LocalVecPlugin.builder().addStore(
 * 				LocalVecConfig.builder().indexName("my-docs").embedderName("openai/text-embedding-3-small").build())
 * 				.build())
 * 		.build();
 * }</pre>
 */
public class LocalVecPlugin implements Plugin {

  private static final Logger logger = LoggerFactory.getLogger(LocalVecPlugin.class);
  public static final String PROVIDER = "devLocalVectorStore";

  private final List<LocalVecConfig> configurations;

  private LocalVecPlugin(List<LocalVecConfig> configurations) {
    this.configurations = configurations;
  }

  /**
   * Creates a builder for LocalVecPlugin.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  @Override
  public String getName() {
    return PROVIDER;
  }

  @Override
  public List<Action<?, ?, ?>> init() {
    // For backward compatibility, but prefer init(Registry)
    return initializeStores(null);
  }

  @Override
  public List<Action<?, ?, ?>> init(Registry registry) {
    return initializeStores(registry);
  }

  private List<Action<?, ?, ?>> initializeStores(Registry registry) {
    List<Action<?, ?, ?>> actions = new ArrayList<>();

    for (LocalVecConfig config : configurations) {
      // Resolve embedder by name if needed
      if (config.getEmbedder() == null && config.getEmbedderName() != null) {
        if (registry == null) {
          throw new IllegalStateException(
              "Registry is required to resolve embedder by name: " + config.getEmbedderName()
                  + ". Use init(Registry) or provide an Embedder instance directly.");
        }
        String embedderKey = ActionType.EMBEDDER.keyFromName(config.getEmbedderName());
        Action<?, ?, ?> embedderAction = registry.lookupAction(embedderKey);
        if (embedderAction == null) {
          throw new IllegalStateException("Embedder not found: " + config.getEmbedderName()
              + ". Make sure the embedder plugin is registered before LocalVecPlugin.");
        }
        if (!(embedderAction instanceof Embedder)) {
          throw new IllegalStateException("Action " + config.getEmbedderName() + " is not an Embedder");
        }
        config.setEmbedder((Embedder) embedderAction);
        logger.info("Resolved embedder: {} for index: {}", config.getEmbedderName(), config.getIndexName());
      }

      logger.info("Initializing local vector store: {}", config.getIndexName());

      LocalVecDocStore docStore = new LocalVecDocStore(config);

      // Create and add retriever
      Retriever retriever = docStore.createRetriever();
      actions.add(retriever);

      // Create and add indexer
      Indexer indexer = docStore.createIndexer();
      actions.add(indexer);

      logger.info("Registered local vector store indexer and retriever: {}", config.getIndexName());
    }

    return actions;
  }

  /**
   * Builder for LocalVecPlugin.
   */
  public static class Builder {
    private final List<LocalVecConfig> configurations = new ArrayList<>();

    /**
     * Adds a vector store configuration.
     *
     * @param config
     *            the configuration
     * @return this builder
     */
    public Builder addStore(LocalVecConfig config) {
      configurations.add(config);
      return this;
    }

    /**
     * Convenience method to add a store with minimal configuration using an
     * embedder instance.
     *
     * @param indexName
     *            the index name
     * @param embedder
     *            the embedder to use
     * @return this builder
     */
    public Builder addStore(String indexName, Embedder embedder) {
      configurations.add(LocalVecConfig.builder().indexName(indexName).embedder(embedder).build());
      return this;
    }

    /**
     * Convenience method to add a store with minimal configuration using an
     * embedder name. The embedder will be resolved from the registry during plugin
     * initialization.
     *
     * @param indexName
     *            the index name
     * @param embedderName
     *            the embedder name (e.g., "openai/text-embedding-3-small")
     * @return this builder
     */
    public Builder addStore(String indexName, String embedderName) {
      configurations.add(LocalVecConfig.builder().indexName(indexName).embedderName(embedderName).build());
      return this;
    }

    /**
     * Builds the plugin.
     *
     * @return the configured plugin
     */
    public LocalVecPlugin build() {
      if (configurations.isEmpty()) {
        throw new IllegalStateException("At least one store configuration is required");
      }
      return new LocalVecPlugin(configurations);
    }
  }
}
