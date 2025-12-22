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

package com.google.genkit.ai.telemetry;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.metrics.LongCounter;
import io.opentelemetry.api.metrics.LongHistogram;
import io.opentelemetry.api.metrics.Meter;

/**
 * ToolTelemetry provides metrics collection for tool execution.
 * 
 * <p>
 * This class tracks:
 * <ul>
 * <li>Tool invocation counts</li>
 * <li>Tool latency histograms</li>
 * <li>Tool error rates</li>
 * </ul>
 */
public class ToolTelemetry {

  private static final Logger logger = LoggerFactory.getLogger(ToolTelemetry.class);
  private static final String METER_NAME = "genkit";
  private static final String SOURCE = "java";

  // Metric names following conventions
  private static final String METRIC_REQUESTS = "genkit/tool/requests";
  private static final String METRIC_LATENCY = "genkit/tool/latency";

  private final LongCounter requestCounter;
  private final LongHistogram latencyHistogram;

  private static ToolTelemetry instance;

  /**
   * Gets the singleton instance of ToolTelemetry.
   *
   * @return the ToolTelemetry instance
   */
  public static synchronized ToolTelemetry getInstance() {
    if (instance == null) {
      instance = new ToolTelemetry();
    }
    return instance;
  }

  private ToolTelemetry() {
    Meter meter = GlobalOpenTelemetry.getMeter(METER_NAME);

    requestCounter = meter.counterBuilder(METRIC_REQUESTS).setDescription("Counts calls to genkit tools.")
        .setUnit("1").build();

    latencyHistogram = meter.histogramBuilder(METRIC_LATENCY)
        .setDescription("Latencies when executing Genkit tools.").setUnit("ms").ofLongs().build();

    logger.debug("ToolTelemetry initialized with OpenTelemetry metrics");
  }

  /**
   * Records metrics for a tool execution.
   *
   * @param toolName
   *            the tool name
   * @param featureName
   *            the feature/flow name
   * @param path
   *            the span path
   * @param latencyMs
   *            the latency in milliseconds
   * @param error
   *            the error name if failed, null otherwise
   */
  public void recordToolMetrics(String toolName, String featureName, String path, long latencyMs, String error) {
    String status = error != null ? "failure" : "success";

    Attributes baseAttrs = Attributes.builder().put("toolName", truncate(toolName, 1024))
        .put("featureName", truncate(featureName, 256)).put("path", truncate(path, 2048)).put("status", status)
        .put("source", SOURCE).build();

    // Record request count
    Attributes requestAttrs = error != null
        ? baseAttrs.toBuilder().put("error", truncate(error, 256)).build()
        : baseAttrs;
    requestCounter.add(1, requestAttrs);

    // Record latency
    latencyHistogram.record(latencyMs, baseAttrs);
  }

  /**
   * Truncates a string to the specified maximum length.
   *
   * @param value
   *            the string to truncate
   * @param maxLength
   *            the maximum length
   * @return the truncated string
   */
  private String truncate(String value, int maxLength) {
    if (value == null) {
      return "";
    }
    if (value.length() <= maxLength) {
      return value;
    }
    return value.substring(0, maxLength);
  }
}
