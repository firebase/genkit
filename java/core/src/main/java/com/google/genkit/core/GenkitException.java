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
 * GenkitException is the base exception for all Genkit errors. It provides
 * structured error information including error codes and details.
 */
public class GenkitException extends RuntimeException {

  private final String errorCode;
  private final Object details;
  private final String traceId;

  /**
   * Creates a new GenkitException.
   *
   * @param message
   *            the error message
   */
  public GenkitException(String message) {
    this(message, null, null, null, null);
  }

  /**
   * Creates a new GenkitException with a cause.
   *
   * @param message
   *            the error message
   * @param cause
   *            the underlying cause
   */
  public GenkitException(String message, Throwable cause) {
    this(message, cause, null, null, null);
  }

  /**
   * Creates a new GenkitException with full details.
   *
   * @param message
   *            the error message
   * @param cause
   *            the underlying cause
   * @param errorCode
   *            the error code
   * @param details
   *            additional error details
   * @param traceId
   *            the trace ID for debugging
   */
  public GenkitException(String message, Throwable cause, String errorCode, Object details, String traceId) {
    super(message, cause);
    this.errorCode = errorCode;
    this.details = details;
    this.traceId = traceId;
  }

  /**
   * Returns the error code.
   *
   * @return the error code, or null if not set
   */
  public String getErrorCode() {
    return errorCode;
  }

  /**
   * Returns additional error details.
   *
   * @return the error details, or null if not set
   */
  public Object getDetails() {
    return details;
  }

  /**
   * Returns the trace ID for this error.
   *
   * @return the trace ID, or null if not set
   */
  public String getTraceId() {
    return traceId;
  }

  /**
   * Creates a builder for GenkitException.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  /**
   * Builder for GenkitException.
   */
  public static class Builder {
    private String message;
    private Throwable cause;
    private String errorCode;
    private Object details;
    private String traceId;

    public Builder message(String message) {
      this.message = message;
      return this;
    }

    public Builder cause(Throwable cause) {
      this.cause = cause;
      return this;
    }

    public Builder errorCode(String errorCode) {
      this.errorCode = errorCode;
      return this;
    }

    public Builder details(Object details) {
      this.details = details;
      return this;
    }

    public Builder traceId(String traceId) {
      this.traceId = traceId;
      return this;
    }

    public GenkitException build() {
      if (message == null || message.isEmpty()) {
        throw new IllegalStateException("message is required");
      }
      return new GenkitException(message, cause, errorCode, details, traceId);
    }
  }
}
