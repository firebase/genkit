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

import com.google.genkit.ai.ModelResponse;
import com.google.genkit.ai.Usage;

import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.metrics.LongCounter;
import io.opentelemetry.api.metrics.LongHistogram;
import io.opentelemetry.api.metrics.Meter;

/**
 * GenerateTelemetry provides metrics collection for model generate actions.
 * 
 * <p>
 * This class tracks:
 * <ul>
 * <li>Request counts per model</li>
 * <li>Latency histograms</li>
 * <li>Input/output token counts</li>
 * <li>Input/output character counts</li>
 * <li>Input/output image counts</li>
 * </ul>
 * 
 * <p>
 * The metrics follow the same naming conventions as the JS and Go SDKs for
 * consistency across the Genkit ecosystem.
 */
public class GenerateTelemetry {

  private static final Logger logger = LoggerFactory.getLogger(GenerateTelemetry.class);
  private static final String METER_NAME = "genkit";
  private static final String SOURCE = "java";

  // Metric names following JS/Go SDK conventions
  private static final String METRIC_REQUESTS = "genkit/ai/generate/requests";
  private static final String METRIC_LATENCY = "genkit/ai/generate/latency";
  private static final String METRIC_INPUT_TOKENS = "genkit/ai/generate/input/tokens";
  private static final String METRIC_OUTPUT_TOKENS = "genkit/ai/generate/output/tokens";
  private static final String METRIC_INPUT_CHARS = "genkit/ai/generate/input/characters";
  private static final String METRIC_OUTPUT_CHARS = "genkit/ai/generate/output/characters";
  private static final String METRIC_INPUT_IMAGES = "genkit/ai/generate/input/images";
  private static final String METRIC_OUTPUT_IMAGES = "genkit/ai/generate/output/images";
  private static final String METRIC_THINKING_TOKENS = "genkit/ai/generate/thinking/tokens";

  private final LongCounter requestCounter;
  private final LongHistogram latencyHistogram;
  private final LongCounter inputTokensCounter;
  private final LongCounter outputTokensCounter;
  private final LongCounter inputCharsCounter;
  private final LongCounter outputCharsCounter;
  private final LongCounter inputImagesCounter;
  private final LongCounter outputImagesCounter;
  private final LongCounter thinkingTokensCounter;

  private static GenerateTelemetry instance;

  /**
   * Gets the singleton instance of GenerateTelemetry.
   *
   * @return the GenerateTelemetry instance
   */
  public static synchronized GenerateTelemetry getInstance() {
    if (instance == null) {
      instance = new GenerateTelemetry();
    }
    return instance;
  }

  private GenerateTelemetry() {
    Meter meter = GlobalOpenTelemetry.getMeter(METER_NAME);

    requestCounter = meter.counterBuilder(METRIC_REQUESTS)
        .setDescription("Counts calls to genkit generate actions.").setUnit("1").build();

    latencyHistogram = meter.histogramBuilder(METRIC_LATENCY)
        .setDescription("Latencies when interacting with a Genkit model.").setUnit("ms").ofLongs().build();

    inputTokensCounter = meter.counterBuilder(METRIC_INPUT_TOKENS)
        .setDescription("Counts input tokens to a Genkit model.").setUnit("1").build();

    outputTokensCounter = meter.counterBuilder(METRIC_OUTPUT_TOKENS)
        .setDescription("Counts output tokens from a Genkit model.").setUnit("1").build();

    inputCharsCounter = meter.counterBuilder(METRIC_INPUT_CHARS)
        .setDescription("Counts input characters to any Genkit model.").setUnit("1").build();

    outputCharsCounter = meter.counterBuilder(METRIC_OUTPUT_CHARS)
        .setDescription("Counts output characters from a Genkit model.").setUnit("1").build();

    inputImagesCounter = meter.counterBuilder(METRIC_INPUT_IMAGES)
        .setDescription("Counts input images to a Genkit model.").setUnit("1").build();

    outputImagesCounter = meter.counterBuilder(METRIC_OUTPUT_IMAGES)
        .setDescription("Count output images from a Genkit model.").setUnit("1").build();

    thinkingTokensCounter = meter.counterBuilder(METRIC_THINKING_TOKENS)
        .setDescription("Counts thinking tokens from a Genkit model.").setUnit("1").build();

    logger.debug("GenerateTelemetry initialized with OpenTelemetry metrics");
  }

  /**
   * Records metrics for a generate action.
   *
   * @param modelName
   *            the model name
   * @param featureName
   *            the feature name (flow name or "generate")
   * @param path
   *            the span path
   * @param response
   *            the model response (may be null)
   * @param latencyMs
   *            the latency in milliseconds
   * @param error
   *            the error name if failed, null otherwise
   */
  public void recordGenerateMetrics(String modelName, String featureName, String path, ModelResponse response,
      long latencyMs, String error) {
    String status = error != null ? "failure" : "success";

    Attributes baseAttrs = Attributes.builder().put("modelName", truncate(modelName, 1024))
        .put("featureName", truncate(featureName, 256)).put("path", truncate(path, 2048)).put("status", status)
        .put("source", SOURCE).build();

    // Record request count
    Attributes requestAttrs = error != null
        ? baseAttrs.toBuilder().put("error", truncate(error, 256)).build()
        : baseAttrs;
    requestCounter.add(1, requestAttrs);

    // Record latency
    latencyHistogram.record(latencyMs, baseAttrs);

    // Record usage metrics if available
    if (response != null && response.getUsage() != null) {
      recordUsageMetrics(response.getUsage(), baseAttrs);
    }
  }

  /**
   * Records usage metrics from a model response.
   *
   * @param usage
   *            the usage statistics
   * @param attrs
   *            the base attributes
   */
  private void recordUsageMetrics(Usage usage, Attributes attrs) {
    if (usage.getInputTokens() != null && usage.getInputTokens() > 0) {
      inputTokensCounter.add(usage.getInputTokens(), attrs);
    }

    if (usage.getOutputTokens() != null && usage.getOutputTokens() > 0) {
      outputTokensCounter.add(usage.getOutputTokens(), attrs);
    }

    if (usage.getInputCharacters() != null && usage.getInputCharacters() > 0) {
      inputCharsCounter.add(usage.getInputCharacters(), attrs);
    }

    if (usage.getOutputCharacters() != null && usage.getOutputCharacters() > 0) {
      outputCharsCounter.add(usage.getOutputCharacters(), attrs);
    }

    if (usage.getInputImages() != null && usage.getInputImages() > 0) {
      inputImagesCounter.add(usage.getInputImages(), attrs);
    }

    if (usage.getOutputImages() != null && usage.getOutputImages() > 0) {
      outputImagesCounter.add(usage.getOutputImages(), attrs);
    }

    if (usage.getThoughtsTokens() != null && usage.getThoughtsTokens() > 0) {
      thinkingTokensCounter.add(usage.getThoughtsTokens(), attrs);
    }
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
