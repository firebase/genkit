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

import com.google.genkit.core.tracing.SpanContext;

/**
 * ActionContext provides context for action execution including tracing and
 * flow information. It is passed to all action executions and carries
 * request-scoped state.
 */
public class ActionContext {

  private final SpanContext spanContext;
  private final String flowName;
  private final String spanPath;
  private final Registry registry;
  private final String sessionId;
  private final String threadName;

  /**
   * Creates a new ActionContext.
   *
   * @param spanContext
   *            the tracing span context, may be null
   * @param flowName
   *            the name of the enclosing flow, may be null
   * @param spanPath
   *            the current span path for tracing
   * @param registry
   *            the Genkit registry
   * @param sessionId
   *            the session ID for multi-turn conversations
   * @param threadName
   *            the thread name for grouping related requests
   */
  public ActionContext(SpanContext spanContext, String flowName, String spanPath, Registry registry, String sessionId,
      String threadName) {
    this.spanContext = spanContext;
    this.flowName = flowName;
    this.spanPath = spanPath;
    this.registry = registry;
    this.sessionId = sessionId;
    this.threadName = threadName;
  }

  /**
   * Creates a new ActionContext.
   *
   * @param spanContext
   *            the tracing span context, may be null
   * @param flowName
   *            the name of the enclosing flow, may be null
   * @param spanPath
   *            the current span path for tracing
   * @param registry
   *            the Genkit registry
   */
  public ActionContext(SpanContext spanContext, String flowName, String spanPath, Registry registry) {
    this(spanContext, flowName, spanPath, registry, null, null);
  }

  /**
   * Creates a new ActionContext.
   *
   * @param spanContext
   *            the tracing span context, may be null
   * @param flowName
   *            the name of the enclosing flow, may be null
   * @param registry
   *            the Genkit registry
   */
  public ActionContext(SpanContext spanContext, String flowName, Registry registry) {
    this(spanContext, flowName, null, registry);
  }

  /**
   * Creates a new ActionContext with default values.
   *
   * @param registry
   *            the Genkit registry
   */
  public ActionContext(Registry registry) {
    this(null, null, null, registry);
  }

  /**
   * Returns the tracing span context.
   *
   * @return the span context, or null if tracing is not active
   */
  public SpanContext getSpanContext() {
    return spanContext;
  }

  /**
   * Returns the name of the enclosing flow, if any.
   *
   * @return the flow name, or null if not in a flow context
   */
  public String getFlowName() {
    return flowName;
  }

  /**
   * Returns the current span path for tracing.
   *
   * @return the span path, or null if not in a traced context
   */
  public String getSpanPath() {
    return spanPath;
  }

  /**
   * Returns the Genkit registry.
   *
   * @return the registry
   */
  public Registry getRegistry() {
    return registry;
  }

  /**
   * Returns the session ID for multi-turn conversations.
   *
   * @return the session ID, or null if not set
   */
  public String getSessionId() {
    return sessionId;
  }

  /**
   * Returns the thread name for grouping related requests.
   *
   * @return the thread name, or null if not set
   */
  public String getThreadName() {
    return threadName;
  }

  /**
   * Creates a new ActionContext with a different flow name.
   *
   * @param flowName
   *            the new flow name
   * @return a new ActionContext with the updated flow name
   */
  public ActionContext withFlowName(String flowName) {
    return new ActionContext(this.spanContext, flowName, this.spanPath, this.registry, this.sessionId,
        this.threadName);
  }

  /**
   * Creates a new ActionContext with a different span context.
   *
   * @param spanContext
   *            the new span context
   * @return a new ActionContext with the updated span context
   */
  public ActionContext withSpanContext(SpanContext spanContext) {
    return new ActionContext(spanContext, this.flowName, this.spanPath, this.registry, this.sessionId,
        this.threadName);
  }

  /**
   * Creates a new ActionContext with a different span path.
   *
   * @param spanPath
   *            the new span path
   * @return a new ActionContext with the updated span path
   */
  public ActionContext withSpanPath(String spanPath) {
    return new ActionContext(this.spanContext, this.flowName, spanPath, this.registry, this.sessionId,
        this.threadName);
  }

  /**
   * Creates a new ActionContext with a session ID.
   *
   * @param sessionId
   *            the session ID
   * @return a new ActionContext with the session ID
   */
  public ActionContext withSessionId(String sessionId) {
    return new ActionContext(this.spanContext, this.flowName, this.spanPath, this.registry, sessionId,
        this.threadName);
  }

  /**
   * Creates a new ActionContext with a thread name.
   *
   * @param threadName
   *            the thread name
   * @return a new ActionContext with the thread name
   */
  public ActionContext withThreadName(String threadName) {
    return new ActionContext(this.spanContext, this.flowName, this.spanPath, this.registry, this.sessionId,
        threadName);
  }

  /**
   * Creates a builder for ActionContext.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  /**
   * Builder for ActionContext.
   */
  public static class Builder {
    private SpanContext spanContext;
    private String flowName;
    private String spanPath;
    private Registry registry;
    private String sessionId;
    private String threadName;

    public Builder spanContext(SpanContext spanContext) {
      this.spanContext = spanContext;
      return this;
    }

    public Builder flowName(String flowName) {
      this.flowName = flowName;
      return this;
    }

    public Builder spanPath(String spanPath) {
      this.spanPath = spanPath;
      return this;
    }

    public Builder registry(Registry registry) {
      this.registry = registry;
      return this;
    }

    public Builder sessionId(String sessionId) {
      this.sessionId = sessionId;
      return this;
    }

    public Builder threadName(String threadName) {
      this.threadName = threadName;
      return this;
    }

    public ActionContext build() {
      if (registry == null) {
        throw new IllegalStateException("registry is required");
      }
      return new ActionContext(spanContext, flowName, spanPath, registry, sessionId, threadName);
    }
  }
}
