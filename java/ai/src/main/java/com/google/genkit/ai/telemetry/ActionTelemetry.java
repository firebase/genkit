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
 * ActionTelemetry provides metrics collection for general action execution.
 * 
 * <p>
 * This class tracks:
 * <ul>
 * <li>Request counts per action type</li>
 * <li>Latency histograms per action</li>
 * <li>Failure counts</li>
 * </ul>
 */
public class ActionTelemetry {

  private static final Logger logger = LoggerFactory.getLogger(ActionTelemetry.class);
  private static final String METER_NAME = "genkit";
  private static final String SOURCE = "java";

  // Metric names following JS/Go SDK conventions
  private static final String METRIC_REQUESTS = "genkit/action/requests";
  private static final String METRIC_LATENCY = "genkit/action/latency";

  private final LongCounter requestCounter;
  private final LongHistogram latencyHistogram;

  private static ActionTelemetry instance;

  /**
   * Gets the singleton instance of ActionTelemetry.
   *
   * @return the ActionTelemetry instance
   */
  public static synchronized ActionTelemetry getInstance() {
    if (instance == null) {
      instance = new ActionTelemetry();
    }
    return instance;
  }

  private ActionTelemetry() {
    Meter meter = GlobalOpenTelemetry.getMeter(METER_NAME);

    requestCounter = meter.counterBuilder(METRIC_REQUESTS).setDescription("Counts calls to genkit actions.")
        .setUnit("1").build();

    latencyHistogram = meter.histogramBuilder(METRIC_LATENCY)
        .setDescription("Latencies when executing Genkit actions.").setUnit("ms").ofLongs().build();

    logger.debug("ActionTelemetry initialized with OpenTelemetry metrics");
  }

  /**
   * Records metrics for an action execution.
   *
   * @param actionName
   *            the action name
   * @param actionType
   *            the action type (flow, model, tool, etc.)
   * @param featureName
   *            the feature name (flow name or action name)
   * @param path
   *            the span path
   * @param latencyMs
   *            the latency in milliseconds
   * @param error
   *            the error name if failed, null otherwise
   */
  public void recordActionMetrics(String actionName, String actionType, String featureName, String path,
      long latencyMs, String error) {
    String status = error != null ? "failure" : "success";

    Attributes baseAttrs = Attributes.builder().put("name", truncate(actionName, 1024))
        .put("type", actionType != null ? actionType : "unknown").put("featureName", truncate(featureName, 256))
        .put("path", truncate(path, 2048)).put("status", status).put("source", SOURCE).build();

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
