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

import java.nio.file.Path;
import java.nio.file.Paths;

import com.google.genkit.ai.Embedder;

/**
 * Configuration for a local vector store.
 */
public class LocalVecConfig {

  private final String indexName;
  private Embedder embedder;
  private final String embedderName;
  private final Path directory;
  private final Object embedderOptions;

  private LocalVecConfig(Builder builder) {
    this.indexName = builder.indexName;
    this.embedder = builder.embedder;
    this.embedderName = builder.embedderName;
    this.directory = builder.directory;
    this.embedderOptions = builder.embedderOptions;
  }

  /**
   * Creates a new builder.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  /**
   * Gets the index name.
   *
   * @return the index name
   */
  public String getIndexName() {
    return indexName;
  }

  /**
   * Gets the embedder.
   *
   * @return the embedder
   */
  public Embedder getEmbedder() {
    return embedder;
  }

  /**
   * Gets the embedder name for deferred resolution.
   *
   * @return the embedder name, or null if embedder was set directly
   */
  public String getEmbedderName() {
    return embedderName;
  }

  /**
   * Sets the embedder (used for deferred resolution).
   *
   * @param embedder
   *            the embedder
   */
  void setEmbedder(Embedder embedder) {
    this.embedder = embedder;
  }

  /**
   * Gets the directory where data is stored.
   *
   * @return the directory path
   */
  public Path getDirectory() {
    return directory;
  }

  /**
   * Gets the embedder options.
   *
   * @return the embedder options, or null
   */
  public Object getEmbedderOptions() {
    return embedderOptions;
  }

  /**
   * Gets the filename for this index.
   *
   * @return the filename
   */
  public String getFilename() {
    return "__db_" + indexName + ".json";
  }

  /**
   * Gets the full path to the data file.
   *
   * @return the full file path
   */
  public Path getFilePath() {
    return directory.resolve(getFilename());
  }

  /**
   * Builder for LocalVecConfig.
   */
  public static class Builder {
    private String indexName;
    private Embedder embedder;
    private String embedderName;
    private Path directory = Paths.get(System.getProperty("java.io.tmpdir"));
    private Object embedderOptions;

    /**
     * Sets the index name.
     *
     * @param indexName
     *            the index name
     * @return this builder
     */
    public Builder indexName(String indexName) {
      this.indexName = indexName;
      return this;
    }

    /**
     * Sets the embedder.
     *
     * @param embedder
     *            the embedder
     * @return this builder
     */
    public Builder embedder(Embedder embedder) {
      this.embedder = embedder;
      return this;
    }

    /**
     * Sets the embedder by name for deferred resolution. The embedder will be
     * resolved from the registry during plugin initialization.
     *
     * @param embedderName
     *            the embedder name (e.g., "openai/text-embedding-3-small")
     * @return this builder
     */
    public Builder embedderName(String embedderName) {
      this.embedderName = embedderName;
      return this;
    }

    /**
     * Sets the directory for storing data.
     *
     * @param directory
     *            the directory path
     * @return this builder
     */
    public Builder directory(Path directory) {
      this.directory = directory;
      return this;
    }

    /**
     * Sets the directory for storing data.
     *
     * @param directory
     *            the directory path as string
     * @return this builder
     */
    public Builder directory(String directory) {
      this.directory = Paths.get(directory);
      return this;
    }

    /**
     * Sets the embedder options.
     *
     * @param embedderOptions
     *            the embedder options
     * @return this builder
     */
    public Builder embedderOptions(Object embedderOptions) {
      this.embedderOptions = embedderOptions;
      return this;
    }

    /**
     * Builds the configuration.
     *
     * @return the configuration
     */
    public LocalVecConfig build() {
      if (indexName == null || indexName.isEmpty()) {
        throw new IllegalStateException("Index name is required");
      }
      if (embedder == null && embedderName == null) {
        throw new IllegalStateException("Either embedder or embedderName is required");
      }
      return new LocalVecConfig(this);
    }
  }
}
