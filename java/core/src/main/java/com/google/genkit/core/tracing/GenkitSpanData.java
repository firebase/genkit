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
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonGetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonSetter;

/**
 * GenkitSpanData represents information about a trace span. This format matches
 * the telemetry server API expectations.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class GenkitSpanData {

  @JsonProperty("spanId")
  private String spanId;

  @JsonProperty("traceId")
  private String traceId;

  @JsonProperty("parentSpanId")
  private String parentSpanId;

  @JsonProperty("startTime")
  private long startTime;

  @JsonProperty("endTime")
  private long endTime;

  @JsonProperty("attributes")
  private Map<String, Object> attributes;

  // displayName is required by the telemetry server schema, so always include it
  // Note: We use @JsonGetter on the getter to ensure the null-check is applied
  // during serialization
  private String displayName = "";

  @JsonProperty("links")
  private List<Link> links;

  @JsonProperty("instrumentationLibrary")
  private InstrumentationScope instrumentationScope;

  @JsonProperty("spanKind")
  private String spanKind;

  @JsonProperty("sameProcessAsParentSpan")
  private BoolValue sameProcessAsParentSpan;

  @JsonProperty("status")
  private Status status;

  @JsonProperty("timeEvents")
  @JsonInclude(JsonInclude.Include.NON_NULL)
  private TimeEvents timeEvents;

  public GenkitSpanData() {
    this.attributes = new HashMap<>();
    this.sameProcessAsParentSpan = new BoolValue(true);
    this.status = new Status();
    // Don't initialize timeEvents - it should be null when there are no events
    // The TypeScript schema defines timeEvents as optional
  }

  // Getters and setters

  public String getSpanId() {
    return spanId;
  }

  public void setSpanId(String spanId) {
    this.spanId = spanId;
  }

  public String getTraceId() {
    return traceId;
  }

  public void setTraceId(String traceId) {
    this.traceId = traceId;
  }

  public String getParentSpanId() {
    return parentSpanId;
  }

  public void setParentSpanId(String parentSpanId) {
    this.parentSpanId = parentSpanId;
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

  public Map<String, Object> getAttributes() {
    return attributes;
  }

  public void setAttributes(Map<String, Object> attributes) {
    this.attributes = attributes;
  }

  public void addAttribute(String key, Object value) {
    this.attributes.put(key, value);
  }

  @JsonGetter("displayName")
  @JsonInclude(JsonInclude.Include.ALWAYS)
  public String getDisplayName() {
    // Never return null - telemetry server requires a string
    return displayName != null ? displayName : "";
  }

  @JsonSetter("displayName")
  public void setDisplayName(String displayName) {
    // Never accept null - telemetry server requires a string
    this.displayName = displayName != null ? displayName : "";
  }

  public List<Link> getLinks() {
    return links;
  }

  public void setLinks(List<Link> links) {
    this.links = links;
  }

  public InstrumentationScope getInstrumentationScope() {
    return instrumentationScope;
  }

  public void setInstrumentationScope(InstrumentationScope instrumentationScope) {
    this.instrumentationScope = instrumentationScope;
  }

  public String getSpanKind() {
    return spanKind;
  }

  public void setSpanKind(String spanKind) {
    this.spanKind = spanKind;
  }

  public BoolValue getSameProcessAsParentSpan() {
    return sameProcessAsParentSpan;
  }

  public void setSameProcessAsParentSpan(BoolValue sameProcessAsParentSpan) {
    this.sameProcessAsParentSpan = sameProcessAsParentSpan;
  }

  public Status getStatus() {
    return status;
  }

  public void setStatus(Status status) {
    this.status = status;
  }

  public TimeEvents getTimeEvents() {
    return timeEvents;
  }

  public void setTimeEvents(TimeEvents timeEvents) {
    this.timeEvents = timeEvents;
  }

  /**
   * BoolValue wraps a boolean to match the expected JSON format.
   */
  public static class BoolValue {
    @JsonProperty("value")
    private boolean value;

    public BoolValue() {
    }

    public BoolValue(boolean value) {
      this.value = value;
    }

    public boolean getValue() {
      return value;
    }

    public void setValue(boolean value) {
      this.value = value;
    }
  }

  /**
   * Status represents the span status.
   */
  public static class Status {
    @JsonProperty("code")
    private int code;

    @JsonProperty("message")
    @JsonInclude(JsonInclude.Include.NON_EMPTY)
    private String message;

    public Status() {
      this.code = 0; // OK
    }

    public Status(int code, String message) {
      this.code = code;
      this.message = message;
    }

    public int getCode() {
      return code;
    }

    public void setCode(int code) {
      this.code = code;
    }

    public String getMessage() {
      return message;
    }

    public void setMessage(String message) {
      this.message = message;
    }
  }

  /**
   * InstrumentationScope represents the instrumentation library.
   */
  public static class InstrumentationScope {
    @JsonProperty("name")
    private String name;

    @JsonProperty("version")
    private String version;

    @JsonProperty("schemaUrl")
    @JsonInclude(JsonInclude.Include.NON_EMPTY)
    private String schemaUrl;

    public InstrumentationScope() {
    }

    public InstrumentationScope(String name, String version) {
      this.name = name;
      this.version = version;
    }

    public String getName() {
      return name;
    }

    public void setName(String name) {
      this.name = name;
    }

    public String getVersion() {
      return version;
    }

    public void setVersion(String version) {
      this.version = version;
    }

    public String getSchemaUrl() {
      return schemaUrl;
    }

    public void setSchemaUrl(String schemaUrl) {
      this.schemaUrl = schemaUrl;
    }
  }

  /**
   * Link describes the relationship between two Spans.
   */
  public static class Link {
    @JsonProperty("context")
    private SpanContextData context;

    @JsonProperty("attributes")
    private Map<String, Object> attributes;

    @JsonProperty("droppedAttributesCount")
    private int droppedAttributesCount;

    public SpanContextData getContext() {
      return context;
    }

    public void setContext(SpanContextData context) {
      this.context = context;
    }

    public Map<String, Object> getAttributes() {
      return attributes;
    }

    public void setAttributes(Map<String, Object> attributes) {
      this.attributes = attributes;
    }

    public int getDroppedAttributesCount() {
      return droppedAttributesCount;
    }

    public void setDroppedAttributesCount(int droppedAttributesCount) {
      this.droppedAttributesCount = droppedAttributesCount;
    }
  }

  /**
   * SpanContextData contains identifying trace information about a Span.
   */
  public static class SpanContextData {
    @JsonProperty("traceId")
    private String traceId;

    @JsonProperty("spanId")
    private String spanId;

    @JsonProperty("isRemote")
    private boolean isRemote;

    @JsonProperty("traceFlags")
    private int traceFlags;

    public String getTraceId() {
      return traceId;
    }

    public void setTraceId(String traceId) {
      this.traceId = traceId;
    }

    public String getSpanId() {
      return spanId;
    }

    public void setSpanId(String spanId) {
      this.spanId = spanId;
    }

    public boolean isRemote() {
      return isRemote;
    }

    public void setRemote(boolean remote) {
      isRemote = remote;
    }

    public int getTraceFlags() {
      return traceFlags;
    }

    public void setTraceFlags(int traceFlags) {
      this.traceFlags = traceFlags;
    }
  }

  /**
   * TimeEvents holds time-based events.
   */
  public static class TimeEvents {
    @JsonProperty("timeEvent")
    private List<TimeEvent> timeEvent;

    public List<TimeEvent> getTimeEvent() {
      return timeEvent;
    }

    public void setTimeEvent(List<TimeEvent> timeEvent) {
      this.timeEvent = timeEvent;
    }
  }

  /**
   * TimeEvent represents a time-based event.
   */
  public static class TimeEvent {
    @JsonProperty("time")
    private long time;

    @JsonProperty("annotation")
    private Annotation annotation;

    public long getTime() {
      return time;
    }

    public void setTime(long time) {
      this.time = time;
    }

    public Annotation getAnnotation() {
      return annotation;
    }

    public void setAnnotation(Annotation annotation) {
      this.annotation = annotation;
    }
  }

  /**
   * Annotation represents an annotation.
   */
  public static class Annotation {
    @JsonProperty("attributes")
    private Map<String, Object> attributes;

    @JsonProperty("description")
    private String description;

    public Map<String, Object> getAttributes() {
      return attributes;
    }

    public void setAttributes(Map<String, Object> attributes) {
      this.attributes = attributes;
    }

    public String getDescription() {
      return description;
    }

    public void setDescription(String description) {
      this.description = description;
    }
  }
}
