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

/**
 * SpanContext contains trace and span identifiers for distributed tracing.
 */
public class SpanContext {

  private final String traceId;
  private final String spanId;
  private final String parentSpanId;

  /**
   * Creates a new SpanContext.
   *
   * @param traceId
   *            the trace ID
   * @param spanId
   *            the span ID
   * @param parentSpanId
   *            the parent span ID, may be null
   */
  public SpanContext(String traceId, String spanId, String parentSpanId) {
    this.traceId = traceId;
    this.spanId = spanId;
    this.parentSpanId = parentSpanId;
  }

  /**
   * Returns the trace ID.
   *
   * @return the trace ID
   */
  public String getTraceId() {
    return traceId;
  }

  /**
   * Returns the span ID.
   *
   * @return the span ID
   */
  public String getSpanId() {
    return spanId;
  }

  /**
   * Returns the parent span ID.
   *
   * @return the parent span ID, or null if this is a root span
   */
  public String getParentSpanId() {
    return parentSpanId;
  }

  /**
   * Returns true if this span has a parent.
   *
   * @return true if this span has a parent
   */
  public boolean hasParent() {
    return parentSpanId != null && !parentSpanId.isEmpty();
  }

  @Override
  public String toString() {
    return "SpanContext{" + "traceId='" + traceId + '\'' + ", spanId='" + spanId + '\'' + ", parentSpanId='"
        + parentSpanId + '\'' + '}';
  }
}
