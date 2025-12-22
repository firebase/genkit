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
 * Request to update an existing dataset.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class UpdateDatasetRequest {

  /**
   * The ID of the dataset to update.
   */
  @JsonProperty("datasetId")
  private String datasetId;

  /**
   * New dataset samples (replaces existing data).
   */
  @JsonProperty("data")
  private List<DatasetSample> data;

  /**
   * New schema for the dataset.
   */
  @JsonProperty("schema")
  private JsonNode schema;

  /**
   * New metric references.
   */
  @JsonProperty("metricRefs")
  private List<String> metricRefs;

  /**
   * New target action.
   */
  @JsonProperty("targetAction")
  private String targetAction;

  public UpdateDatasetRequest() {
  }

  private UpdateDatasetRequest(Builder builder) {
    this.datasetId = builder.datasetId;
    this.data = builder.data;
    this.schema = builder.schema;
    this.metricRefs = builder.metricRefs;
    this.targetAction = builder.targetAction;
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

  public List<DatasetSample> getData() {
    return data;
  }

  public void setData(List<DatasetSample> data) {
    this.data = data;
  }

  public JsonNode getSchema() {
    return schema;
  }

  public void setSchema(JsonNode schema) {
    this.schema = schema;
  }

  public List<String> getMetricRefs() {
    return metricRefs;
  }

  public void setMetricRefs(List<String> metricRefs) {
    this.metricRefs = metricRefs;
  }

  public String getTargetAction() {
    return targetAction;
  }

  public void setTargetAction(String targetAction) {
    this.targetAction = targetAction;
  }

  public static class Builder {
    private String datasetId;
    private List<DatasetSample> data;
    private JsonNode schema;
    private List<String> metricRefs;
    private String targetAction;

    public Builder datasetId(String datasetId) {
      this.datasetId = datasetId;
      return this;
    }

    public Builder data(List<DatasetSample> data) {
      this.data = data;
      return this;
    }

    public Builder schema(JsonNode schema) {
      this.schema = schema;
      return this;
    }

    public Builder metricRefs(List<String> metricRefs) {
      this.metricRefs = metricRefs;
      return this;
    }

    public Builder targetAction(String targetAction) {
      this.targetAction = targetAction;
      return this;
    }

    public UpdateDatasetRequest build() {
      return new UpdateDatasetRequest(this);
    }
  }
}
