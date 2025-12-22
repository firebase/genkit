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

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.BiFunction;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;

import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.SpanKind;
import io.opentelemetry.api.trace.StatusCode;
import io.opentelemetry.context.Scope;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.trace.SdkTracerProvider;

/**
 * Tracer provides tracing utilities for Genkit operations. It integrates with
 * OpenTelemetry for distributed tracing.
 */
public final class Tracer {

  private static final Logger logger = LoggerFactory.getLogger(Tracer.class);
  private static final String INSTRUMENTATION_NAME = "genkit-java";
  private static final AtomicBoolean initialized = new AtomicBoolean(false);
  private static final ObjectMapper objectMapper = new ObjectMapper();
  private static volatile io.opentelemetry.api.trace.Tracer otelTracer;
  private static volatile TelemetryServerExporter telemetryExporter;
  private static volatile SdkTracerProvider tracerProvider;
  private static volatile String configuredTelemetryServerUrl;

  static {
    initializeTracer();
  }

  private Tracer() {
    // Utility class
  }

  /**
   * Initializes the OpenTelemetry tracer with the telemetry exporter.
   */
  private static synchronized void initializeTracer() {
    if (initialized.compareAndSet(false, true)) {
      try {
        // Create the telemetry exporter
        telemetryExporter = new TelemetryServerExporter();

        // Create SDK tracer provider with our exporter
        tracerProvider = SdkTracerProvider.builder().addSpanProcessor(telemetryExporter).build();

        // Build the OpenTelemetry SDK - try to register globally
        OpenTelemetrySdk openTelemetry;
        try {
          openTelemetry = OpenTelemetrySdk.builder().setTracerProvider(tracerProvider)
              .buildAndRegisterGlobal();
        } catch (IllegalStateException e) {
          // GlobalOpenTelemetry was already set - just build without registering
          logger.debug("GlobalOpenTelemetry already set, building local SDK: {}", e.getMessage());
          openTelemetry = OpenTelemetrySdk.builder().setTracerProvider(tracerProvider).build();
        }

        otelTracer = openTelemetry.getTracer(INSTRUMENTATION_NAME);

        logger.debug("OpenTelemetry tracer initialized with telemetry exporter");
      } catch (Exception e) {
        logger.error("Failed to initialize OpenTelemetry tracer", e);
      }

      // Check for environment variable for telemetry server
      String telemetryServerUrl = System.getenv("GENKIT_TELEMETRY_SERVER");
      if (telemetryServerUrl != null && !telemetryServerUrl.isEmpty()) {
        configureTelemetryServer(telemetryServerUrl);
      }
    }
  }

  /**
   * Configures the telemetry server URL for exporting traces. This is typically
   * called when the CLI notifies the runtime of the telemetry server URL.
   *
   * @param serverUrl
   *            the telemetry server URL
   */
  public static void configureTelemetryServer(String serverUrl) {
    if (serverUrl != null && !serverUrl.isEmpty() && telemetryExporter != null) {
      // Skip if already configured with the same URL
      if (serverUrl.equals(configuredTelemetryServerUrl)) {
        return;
      }
      telemetryExporter.setClient(new HttpTelemetryClient(serverUrl));
      configuredTelemetryServerUrl = serverUrl;
      logger.info("Connected to telemetry server: {}", serverUrl);
    }
  }

  /**
   * Returns true if the telemetry exporter is configured.
   */
  public static boolean isTelemetryConfigured() {
    return telemetryExporter != null && telemetryExporter.isConfigured();
  }

  /**
   * Runs a function within a new tracing span.
   *
   * @param ctx
   *            the action context
   * @param metadata
   *            the span metadata
   * @param input
   *            the input to pass to the function
   * @param fn
   *            the function to execute
   * @param <I>
   *            the input type
   * @param <O>
   *            the output type
   * @return the function result
   * @throws GenkitException
   *             if the function throws an exception
   */
  public static <I, O> O runInNewSpan(ActionContext ctx, SpanMetadata metadata, I input,
      BiFunction<SpanContext, I, O> fn) throws GenkitException {
    String spanName = metadata.getName() != null ? metadata.getName() : "unknown";

    // Determine if this is a root span
    boolean isRoot = ctx.getSpanContext() == null;

    // Build the path for this span
    String parentPath = isRoot ? "" : ctx.getSpanPath();
    String path = buildPath(spanName, parentPath, metadata.getType(), metadata.getSubtype());

    Span span = otelTracer.spanBuilder(spanName).setSpanKind(SpanKind.INTERNAL).startSpan();

    // Add genkit-specific attributes
    span.setAttribute("genkit:name", spanName);
    span.setAttribute("genkit:path", path);
    span.setAttribute("genkit:isRoot", isRoot);

    // Add input as JSON
    if (input != null) {
      try {
        span.setAttribute("genkit:input", objectMapper.writeValueAsString(input));
      } catch (JsonProcessingException e) {
        span.setAttribute("genkit:input", input.toString());
      }
    }

    // Add attributes from metadata
    if (metadata.getType() != null) {
      span.setAttribute("genkit:type", metadata.getType());
    }
    if (metadata.getSubtype() != null) {
      // Use genkit:metadata:subtype to match JS/Go SDK format
      span.setAttribute("genkit:metadata:subtype", metadata.getSubtype());
    }

    // Add session and thread info from context for multi-turn conversation tracking
    if (ctx.getSessionId() != null) {
      span.setAttribute("genkit:sessionId", ctx.getSessionId());
    }
    if (ctx.getThreadName() != null) {
      span.setAttribute("genkit:threadName", ctx.getThreadName());
    }

    if (metadata.getAttributes() != null) {
      for (Map.Entry<String, Object> entry : metadata.getAttributes().entrySet()) {
        if (entry.getValue() instanceof String) {
          span.setAttribute(entry.getKey(), (String) entry.getValue());
        } else if (entry.getValue() instanceof Long) {
          span.setAttribute(entry.getKey(), (Long) entry.getValue());
        } else if (entry.getValue() instanceof Double) {
          span.setAttribute(entry.getKey(), (Double) entry.getValue());
        } else if (entry.getValue() instanceof Boolean) {
          span.setAttribute(entry.getKey(), (Boolean) entry.getValue());
        } else if (entry.getValue() != null) {
          span.setAttribute(entry.getKey(), entry.getValue().toString());
        }
      }
    }

    io.opentelemetry.api.trace.SpanContext otelSpanContext = span.getSpanContext();
    SpanContext spanContext = new SpanContext(otelSpanContext.getTraceId(), otelSpanContext.getSpanId(),
        ctx.getSpanContext() != null ? ctx.getSpanContext().getSpanId() : null);

    try (Scope scope = span.makeCurrent()) {
      O result = fn.apply(spanContext, input);

      // Add output as JSON
      if (result != null) {
        try {
          span.setAttribute("genkit:output", objectMapper.writeValueAsString(result));
        } catch (JsonProcessingException e) {
          span.setAttribute("genkit:output", result.toString());
        }
      }

      span.setAttribute("genkit:state", "success");
      span.setStatus(StatusCode.OK);
      return result;
    } catch (GenkitException e) {
      span.setAttribute("genkit:state", "error");
      span.setStatus(StatusCode.ERROR, e.getMessage());
      span.recordException(e);
      throw e;
    } catch (RuntimeException e) {
      // Re-throw RuntimeExceptions as-is (includes AgentHandoffException,
      // ToolInterruptException, etc.)
      span.setAttribute("genkit:state", "error");
      span.setStatus(StatusCode.ERROR, e.getMessage());
      span.recordException(e);
      throw e;
    } catch (Exception e) {
      span.setAttribute("genkit:state", "error");
      span.setStatus(StatusCode.ERROR, e.getMessage());
      span.recordException(e);
      throw new GenkitException("Span execution failed: " + e.getMessage(), e);
    } finally {
      span.end();
    }
  }

  /**
   * Builds an annotated path for the span. Format:
   * /{name,t:type}/{name,t:type,s:subtype}
   */
  private static String buildPath(String name, String parentPath, String type, String subtype) {
    StringBuilder segment = new StringBuilder("{").append(name);
    if (type != null && !type.isEmpty()) {
      segment.append(",t:").append(type);
    }
    if (subtype != null && !subtype.isEmpty()) {
      segment.append(",s:").append(subtype);
    }
    segment.append("}");

    return (parentPath != null ? parentPath : "") + "/" + segment;
  }

  /**
   * Creates a new root span context.
   *
   * @return a new SpanContext with a unique trace ID
   */
  public static SpanContext newRootSpanContext() {
    String traceId = UUID.randomUUID().toString().replace("-", "");
    String spanId = UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    return new SpanContext(traceId, spanId, null);
  }

  /**
   * Creates a child span context from a parent.
   *
   * @param parent
   *            the parent span context
   * @return a new child SpanContext
   */
  public static SpanContext newChildSpanContext(SpanContext parent) {
    String spanId = UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    return new SpanContext(parent.getTraceId(), spanId, parent.getSpanId());
  }

  /**
   * Adds an event to the current span.
   *
   * @param name
   *            the event name
   * @param attributes
   *            the event attributes
   */
  public static void addEvent(String name, Map<String, String> attributes) {
    Span currentSpan = Span.current();
    if (currentSpan != null) {
      io.opentelemetry.api.common.AttributesBuilder attrBuilder = io.opentelemetry.api.common.Attributes
          .builder();
      if (attributes != null) {
        for (Map.Entry<String, String> entry : attributes.entrySet()) {
          attrBuilder.put(entry.getKey(), entry.getValue());
        }
      }
      currentSpan.addEvent(name, attrBuilder.build());
    }
  }

  /**
   * Records an exception on the current span.
   *
   * @param exception
   *            the exception to record
   */
  public static void recordException(Throwable exception) {
    Span currentSpan = Span.current();
    if (currentSpan != null) {
      currentSpan.recordException(exception);
    }
  }
}
