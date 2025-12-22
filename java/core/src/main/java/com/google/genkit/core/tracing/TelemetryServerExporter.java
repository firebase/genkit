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

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import io.opentelemetry.api.trace.StatusCode;
import io.opentelemetry.context.Context;
import io.opentelemetry.sdk.common.CompletableResultCode;
import io.opentelemetry.sdk.trace.SpanProcessor;
import io.opentelemetry.sdk.trace.data.EventData;
import io.opentelemetry.sdk.trace.data.LinkData;
import io.opentelemetry.sdk.trace.data.SpanData;

/**
 * OpenTelemetry SpanProcessor that exports spans to the Genkit telemetry
 * server. This enables traces to be visible in the Genkit Developer UI.
 */
public class TelemetryServerExporter implements SpanProcessor {

  private static final Logger logger = LoggerFactory.getLogger(TelemetryServerExporter.class);
  private static final String INSTRUMENTATION_NAME = "genkit-java";
  private static final String INSTRUMENTATION_VERSION = "1.0.0";

  private final AtomicReference<TelemetryClient> clientRef = new AtomicReference<>();

  // Buffer spans by trace ID to send complete traces
  private final Map<String, TraceData> traceBuffer = new ConcurrentHashMap<>();

  /**
   * Creates a new TelemetryServerExporter.
   */
  public TelemetryServerExporter() {
  }

  /**
   * Sets the telemetry client to use for exporting traces.
   *
   * @param client
   *            the telemetry client
   */
  public void setClient(TelemetryClient client) {
    this.clientRef.set(client);
    logger.debug("Telemetry client configured");
  }

  /**
   * Returns true if the exporter is configured with a client.
   */
  public boolean isConfigured() {
    return clientRef.get() != null;
  }

  @Override
  public void onStart(Context parentContext, io.opentelemetry.sdk.trace.ReadWriteSpan span) {
    // No action needed on start
  }

  @Override
  public boolean isStartRequired() {
    return false;
  }

  @Override
  public void onEnd(io.opentelemetry.sdk.trace.ReadableSpan span) {
    TelemetryClient client = clientRef.get();
    if (client == null) {
      logger.trace("No telemetry client configured, skipping span export");
      return;
    }

    try {
      SpanData otelSpanData = span.toSpanData();
      String traceId = otelSpanData.getTraceId();
      String spanId = otelSpanData.getSpanId();

      // Convert OpenTelemetry span to our format
      GenkitSpanData genkitSpanData = convertSpan(otelSpanData);

      // Get or create trace data
      TraceData traceData = traceBuffer.computeIfAbsent(traceId, TraceData::new);
      traceData.addSpan(genkitSpanData);

      // If this is a root span (no parent), set trace-level info and export
      String parentSpanId = otelSpanData.getParentSpanId();
      if (parentSpanId == null || parentSpanId.isEmpty() || "0000000000000000".equals(parentSpanId)) {
        traceData.setDisplayName(otelSpanData.getName());
        traceData.setStartTime(toMillis(otelSpanData.getStartEpochNanos()));
        traceData.setEndTime(toMillis(otelSpanData.getEndEpochNanos()));

        // Export the trace
        exportTrace(client, traceData);

        // Remove from buffer
        traceBuffer.remove(traceId);
      } else {
        // For non-root spans, still try to export incrementally
        // This ensures traces show up in the UI even before completion
        exportTrace(client, traceData);
      }

    } catch (Exception e) {
      logger.error("Failed to export span to telemetry server", e);
    }
  }

  @Override
  public boolean isEndRequired() {
    return true;
  }

  @Override
  public CompletableResultCode shutdown() {
    // Export any remaining buffered traces
    TelemetryClient client = clientRef.get();
    if (client != null) {
      for (TraceData trace : traceBuffer.values()) {
        try {
          client.save(trace);
        } catch (Exception e) {
          logger.error("Failed to export trace during shutdown", e);
        }
      }
    }
    traceBuffer.clear();
    return CompletableResultCode.ofSuccess();
  }

  @Override
  public CompletableResultCode forceFlush() {
    // Export all buffered traces
    TelemetryClient client = clientRef.get();
    if (client != null) {
      for (Map.Entry<String, TraceData> entry : traceBuffer.entrySet()) {
        try {
          client.save(entry.getValue());
        } catch (Exception e) {
          logger.error("Failed to export trace during flush", e);
        }
      }
    }
    return CompletableResultCode.ofSuccess();
  }

  private void exportTrace(TelemetryClient client, TraceData traceData) {
    try {
      client.save(traceData);
    } catch (Exception e) {
      logger.error("Failed to export trace: traceId={}", traceData.getTraceId(), e);
    }
  }

  private GenkitSpanData convertSpan(SpanData otelSpan) {
    GenkitSpanData span = new GenkitSpanData();

    span.setSpanId(otelSpan.getSpanId());
    span.setTraceId(otelSpan.getTraceId());
    // displayName is required by the telemetry server schema - ensure it's never
    // null
    String spanName = otelSpan.getName();
    span.setDisplayName(spanName != null ? spanName : "unknown");
    span.setStartTime(toMillis(otelSpan.getStartEpochNanos()));
    span.setEndTime(toMillis(otelSpan.getEndEpochNanos()));
    span.setSpanKind(otelSpan.getKind().name());

    String parentSpanId = otelSpan.getParentSpanId();
    if (parentSpanId != null && !parentSpanId.isEmpty() && !"0000000000000000".equals(parentSpanId)) {
      span.setParentSpanId(parentSpanId);
    }

    // Convert attributes
    Map<String, Object> attributes = new HashMap<>();
    otelSpan.getAttributes().forEach((key, value) -> {
      attributes.put(key.getKey(), value);
    });
    span.setAttributes(attributes);

    // Convert status
    GenkitSpanData.Status status = new GenkitSpanData.Status();
    status.setCode(convertStatusCode(otelSpan.getStatus().getStatusCode()));
    if (otelSpan.getStatus().getDescription() != null) {
      status.setMessage(otelSpan.getStatus().getDescription());
    }
    span.setStatus(status);

    // Set instrumentation scope - name is required by the schema
    GenkitSpanData.InstrumentationScope scope = new GenkitSpanData.InstrumentationScope();
    String scopeName = otelSpan.getInstrumentationScopeInfo().getName();
    scope.setName(scopeName != null && !scopeName.isEmpty() ? scopeName : "genkit-java");
    // Version is optional but default to 1.0.0 if not set
    String version = otelSpan.getInstrumentationScopeInfo().getVersion();
    scope.setVersion(version != null ? version : "1.0.0");
    span.setInstrumentationScope(scope);

    // Convert events to time events
    List<EventData> events = otelSpan.getEvents();
    if (events != null && !events.isEmpty()) {
      GenkitSpanData.TimeEvents timeEvents = new GenkitSpanData.TimeEvents();
      List<GenkitSpanData.TimeEvent> timeEventList = new ArrayList<>();

      for (EventData event : events) {
        GenkitSpanData.TimeEvent timeEvent = new GenkitSpanData.TimeEvent();
        timeEvent.setTime(toMillis(event.getEpochNanos()));

        GenkitSpanData.Annotation annotation = new GenkitSpanData.Annotation();
        annotation.setDescription(event.getName());

        Map<String, Object> eventAttrs = new HashMap<>();
        event.getAttributes().forEach((key, value) -> {
          eventAttrs.put(key.getKey(), value);
        });
        annotation.setAttributes(eventAttrs);

        timeEvent.setAnnotation(annotation);
        timeEventList.add(timeEvent);
      }

      timeEvents.setTimeEvent(timeEventList);
      span.setTimeEvents(timeEvents);
    }

    // Convert links
    List<LinkData> links = otelSpan.getLinks();
    if (links != null && !links.isEmpty()) {
      List<GenkitSpanData.Link> linkList = new ArrayList<>();
      for (LinkData link : links) {
        GenkitSpanData.Link l = new GenkitSpanData.Link();

        GenkitSpanData.SpanContextData ctx = new GenkitSpanData.SpanContextData();
        ctx.setTraceId(link.getSpanContext().getTraceId());
        ctx.setSpanId(link.getSpanContext().getSpanId());
        ctx.setRemote(link.getSpanContext().isRemote());
        ctx.setTraceFlags(link.getSpanContext().getTraceFlags().asByte());
        l.setContext(ctx);

        Map<String, Object> linkAttrs = new HashMap<>();
        link.getAttributes().forEach((key, value) -> {
          linkAttrs.put(key.getKey(), value);
        });
        l.setAttributes(linkAttrs);
        l.setDroppedAttributesCount(link.getTotalAttributeCount() - link.getAttributes().size());

        linkList.add(l);
      }
      span.setLinks(linkList);
    }

    // Set sameProcessAsParentSpan
    span.setSameProcessAsParentSpan(new GenkitSpanData.BoolValue(!otelSpan.getSpanContext().isRemote()));

    return span;
  }

  private int convertStatusCode(StatusCode statusCode) {
    switch (statusCode) {
      case OK :
        return 0;
      case ERROR :
        return 2;
      case UNSET :
      default :
        return 0;
    }
  }

  private long toMillis(long nanos) {
    return TimeUnit.NANOSECONDS.toMillis(nanos);
  }
}
