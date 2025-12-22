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
 * FeatureTelemetry provides metrics collection for top-level feature (flow)
 * execution.
 * 
 * <p>
 * This class tracks:
 * <ul>
 * <li>Feature request counts</li>
 * <li>Feature latency histograms</li>
 * <li>Path-level metrics for observability</li>
 * </ul>
 * 
 * <p>
 * Features in Genkit are the entry points to AI functionality, typically flows
 * that users interact with directly.
 */
public class FeatureTelemetry {

  private static final Logger logger = LoggerFactory.getLogger(FeatureTelemetry.class);
  private static final String METER_NAME = "genkit";
  private static final String SOURCE = "java";

  // Feature-level metrics
  private static final String METRIC_FEATURE_REQUESTS = "genkit/feature/requests";
  private static final String METRIC_FEATURE_LATENCY = "genkit/feature/latency";

  // Path-level metrics
  private static final String METRIC_PATH_REQUESTS = "genkit/feature/path/requests";
  private static final String METRIC_PATH_LATENCY = "genkit/feature/path/latency";

  private final LongCounter featureRequestCounter;
  private final LongHistogram featureLatencyHistogram;
  private final LongCounter pathRequestCounter;
  private final LongHistogram pathLatencyHistogram;

  private static FeatureTelemetry instance;

  /**
   * Gets the singleton instance of FeatureTelemetry.
   *
   * @return the FeatureTelemetry instance
   */
  public static synchronized FeatureTelemetry getInstance() {
    if (instance == null) {
      instance = new FeatureTelemetry();
    }
    return instance;
  }

  private FeatureTelemetry() {
    Meter meter = GlobalOpenTelemetry.getMeter(METER_NAME);

    featureRequestCounter = meter.counterBuilder(METRIC_FEATURE_REQUESTS)
        .setDescription("Counts calls to genkit features (flows).").setUnit("1").build();

    featureLatencyHistogram = meter.histogramBuilder(METRIC_FEATURE_LATENCY)
        .setDescription("Latencies when executing Genkit features.").setUnit("ms").ofLongs().build();

    pathRequestCounter = meter.counterBuilder(METRIC_PATH_REQUESTS)
        .setDescription("Tracks unique flow paths per flow.").setUnit("1").build();

    pathLatencyHistogram = meter.histogramBuilder(METRIC_PATH_LATENCY).setDescription("Latencies per flow path.")
        .setUnit("ms").ofLongs().build();

    logger.debug("FeatureTelemetry initialized with OpenTelemetry metrics");
  }

  /**
   * Records metrics for a feature (root flow) execution.
   *
   * @param featureName
   *            the feature name
   * @param path
   *            the span path
   * @param latencyMs
   *            the latency in milliseconds
   * @param error
   *            the error name if failed, null otherwise
   */
  public void recordFeatureMetrics(String featureName, String path, long latencyMs, String error) {
    String status = error != null ? "failure" : "success";

    Attributes attrs = Attributes.builder().put("featureName", truncate(featureName, 256))
        .put("path", truncate(path, 2048)).put("status", status).put("source", SOURCE).build();

    featureRequestCounter.add(1,
        error != null ? attrs.toBuilder().put("error", truncate(error, 256)).build() : attrs);
    featureLatencyHistogram.record(latencyMs, attrs);
  }

  /**
   * Records metrics for a path within a flow.
   *
   * @param featureName
   *            the feature name
   * @param path
   *            the full path including step types
   * @param latencyMs
   *            the latency in milliseconds
   * @param error
   *            the error name if failed, null otherwise
   */
  public void recordPathMetrics(String featureName, String path, long latencyMs, String error) {
    String status = error != null ? "failure" : "success";
    String simplePath = extractSimplePathFromQualified(path);

    Attributes attrs = Attributes.builder().put("featureName", truncate(featureName, 256))
        .put("path", truncate(simplePath, 2048)).put("status", status).put("source", SOURCE).build();

    pathRequestCounter.add(1, error != null ? attrs.toBuilder().put("error", truncate(error, 256)).build() : attrs);
    pathLatencyHistogram.record(latencyMs, attrs);
  }

  /**
   * Extracts a simple path name from a qualified path. For example:
   * /{flow,t:flow}/{step,t:action} -> flow/step
   *
   * @param qualifiedPath
   *            the qualified path with type annotations
   * @return the simple path
   */
  private String extractSimplePathFromQualified(String qualifiedPath) {
    if (qualifiedPath == null || qualifiedPath.isEmpty()) {
      return "";
    }

    StringBuilder simplePath = new StringBuilder();
    String[] parts = qualifiedPath.split("/");

    for (String part : parts) {
      if (part.isEmpty())
        continue;

      // Extract name from {name,t:type} format
      if (part.startsWith("{") && part.contains(",")) {
        String name = part.substring(1, part.indexOf(','));
        if (simplePath.length() > 0) {
          simplePath.append("/");
        }
        simplePath.append(name);
      } else if (part.startsWith("{") && part.endsWith("}")) {
        String name = part.substring(1, part.length() - 1);
        if (simplePath.length() > 0) {
          simplePath.append("/");
        }
        simplePath.append(name);
      }
    }

    return simplePath.toString();
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
