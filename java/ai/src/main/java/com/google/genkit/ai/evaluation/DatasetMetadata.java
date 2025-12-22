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

package com.google.genkit.ai.evaluation;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;

/**
 * Metadata about a dataset stored in the dataset store.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DatasetMetadata {

  /**
   * Unique identifier for the dataset.
   */
  @JsonProperty("datasetId")
  private String datasetId;

  /**
   * Number of samples in the dataset.
   */
  @JsonProperty("size")
  private int size;

  /**
   * Optional schema definition for the dataset.
   */
  @JsonProperty("schema")
  private JsonNode schema;

  /**
   * The type of dataset (FLOW, MODEL, etc.).
   */
  @JsonProperty("datasetType")
  private DatasetType datasetType;

  /**
   * The action this dataset is designed for.
   */
  @JsonProperty("targetAction")
  private String targetAction;

  /**
   * References to metrics/evaluators to use with this dataset.
   */
  @JsonProperty("metricRefs")
  private List<String> metricRefs;

  /**
   * Version number of the dataset.
   */
  @JsonProperty("version")
  private int version;

  /**
   * Timestamp when the dataset was created.
   */
  @JsonProperty("createTime")
  private String createTime;

  /**
   * Timestamp when the dataset was last updated.
   */
  @JsonProperty("updateTime")
  private String updateTime;

  public DatasetMetadata() {
  }

  private DatasetMetadata(Builder builder) {
    this.datasetId = builder.datasetId;
    this.size = builder.size;
    this.schema = builder.schema;
    this.datasetType = builder.datasetType;
    this.targetAction = builder.targetAction;
    this.metricRefs = builder.metricRefs;
    this.version = builder.version;
    this.createTime = builder.createTime;
    this.updateTime = builder.updateTime;
  }

  public static Builder builder() {
    return new Builder();
  }

  public String getDatasetId() {
    return datasetId;
  }

  public void setDatasetId(String datasetId) {
    this.datasetId = datasetId;
  }

  public int getSize() {
    return size;
  }

  public void setSize(int size) {
    this.size = size;
  }

  public JsonNode getSchema() {
    return schema;
  }

  public void setSchema(JsonNode schema) {
    this.schema = schema;
  }

  public DatasetType getDatasetType() {
    return datasetType;
  }

  public void setDatasetType(DatasetType datasetType) {
    this.datasetType = datasetType;
  }

  public String getTargetAction() {
    return targetAction;
  }

  public void setTargetAction(String targetAction) {
    this.targetAction = targetAction;
  }

  public List<String> getMetricRefs() {
    return metricRefs;
  }

  public void setMetricRefs(List<String> metricRefs) {
    this.metricRefs = metricRefs;
  }

  public int getVersion() {
    return version;
  }

  public void setVersion(int version) {
    this.version = version;
  }

  public String getCreateTime() {
    return createTime;
  }

  public void setCreateTime(String createTime) {
    this.createTime = createTime;
  }

  public String getUpdateTime() {
    return updateTime;
  }

  public void setUpdateTime(String updateTime) {
    this.updateTime = updateTime;
  }

  public static class Builder {
    private String datasetId;
    private int size;
    private JsonNode schema;
    private DatasetType datasetType = DatasetType.UNKNOWN;
    private String targetAction;
    private List<String> metricRefs;
    private int version = 1;
    private String createTime;
    private String updateTime;

    public Builder datasetId(String datasetId) {
      this.datasetId = datasetId;
      return this;
    }

    public Builder size(int size) {
      this.size = size;
      return this;
    }

    public Builder schema(JsonNode schema) {
      this.schema = schema;
      return this;
    }

    public Builder datasetType(DatasetType datasetType) {
      this.datasetType = datasetType;
      return this;
    }

    public Builder targetAction(String targetAction) {
      this.targetAction = targetAction;
      return this;
    }

    public Builder metricRefs(List<String> metricRefs) {
      this.metricRefs = metricRefs;
      return this;
    }

    public Builder version(int version) {
      this.version = version;
      return this;
    }

    public Builder createTime(String createTime) {
      this.createTime = createTime;
      return this;
    }

    public Builder updateTime(String updateTime) {
      this.updateTime = updateTime;
      return this;
    }

    public DatasetMetadata build() {
      return new DatasetMetadata(this);
    }
  }
}
