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

package com.google.genkit.core.tracing;

import java.util.HashMap;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * TraceData represents a complete trace with all its spans. This format matches
 * the telemetry server API expectations.
 */
public class TraceData {

  @JsonProperty("traceId")
  private String traceId;

  @JsonProperty("displayName")
  @JsonInclude(JsonInclude.Include.NON_NULL)
  private String displayName;

  @JsonProperty("startTime")
  private long startTime;

  @JsonProperty("endTime")
  private long endTime;

  @JsonProperty("spans")
  private Map<String, GenkitSpanData> spans;

  public TraceData() {
    this.spans = new HashMap<>();
  }

  public TraceData(String traceId) {
    this.traceId = traceId;
    this.spans = new HashMap<>();
  }

  public String getTraceId() {
    return traceId;
  }

  public void setTraceId(String traceId) {
    this.traceId = traceId;
  }

  public String getDisplayName() {
    return displayName;
  }

  public void setDisplayName(String displayName) {
    this.displayName = displayName;
  }

  public long getStartTime() {
    return startTime;
  }

  public void setStartTime(long startTime) {
    this.startTime = startTime;
  }

  public long getEndTime() {
    return endTime;
  }

  public void setEndTime(long endTime) {
    this.endTime = endTime;
  }

  public Map<String, GenkitSpanData> getSpans() {
    return spans;
  }

  public void setSpans(Map<String, GenkitSpanData> spans) {
    this.spans = spans;
  }

  public void addSpan(GenkitSpanData span) {
    this.spans.put(span.getSpanId(), span);
  }
}
