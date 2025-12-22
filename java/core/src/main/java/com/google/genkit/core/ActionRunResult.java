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

package com.google.genkit.core;

/**
 * ActionRunResult contains the result of an action execution along with
 * telemetry information.
 *
 * @param <T>
 *            the type of the result
 */
public class ActionRunResult<T> {

  private final T result;
  private final String traceId;
  private final String spanId;

  /**
   * Creates a new ActionRunResult.
   *
   * @param result
   *            the action result
   * @param traceId
   *            the trace ID for this execution
   * @param spanId
   *            the span ID for this execution
   */
  public ActionRunResult(T result, String traceId, String spanId) {
    this.result = result;
    this.traceId = traceId;
    this.spanId = spanId;
  }

  /**
   * Returns the action result.
   *
   * @return the result
   */
  public T getResult() {
    return result;
  }

  /**
   * Returns the trace ID for this execution.
   *
   * @return the trace ID
   */
  public String getTraceId() {
    return traceId;
  }

  /**
   * Returns the span ID for this execution.
   *
   * @return the span ID
   */
  public String getSpanId() {
    return spanId;
  }

  /**
   * Creates a builder for ActionRunResult.
   *
   * @param <T>
   *            the result type
   * @return a new builder
   */
  public static <T> Builder<T> builder() {
    return new Builder<>();
  }

  /**
   * Builder for ActionRunResult.
   *
   * @param <T>
   *            the result type
   */
  public static class Builder<T> {
    private T result;
    private String traceId;
    private String spanId;

    public Builder<T> result(T result) {
      this.result = result;
      return this;
    }

    public Builder<T> traceId(String traceId) {
      this.traceId = traceId;
      return this;
    }

    public Builder<T> spanId(String spanId) {
      this.spanId = spanId;
      return this;
    }

    public ActionRunResult<T> build() {
      return new ActionRunResult<>(result, traceId, spanId);
    }
  }
}
