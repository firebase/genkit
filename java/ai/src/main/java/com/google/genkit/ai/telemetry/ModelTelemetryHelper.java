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

import com.google.genkit.ai.Message;
import com.google.genkit.ai.ModelRequest;
import com.google.genkit.ai.ModelResponse;
import com.google.genkit.ai.Part;
import com.google.genkit.ai.Usage;
import com.google.genkit.core.GenkitException;

/**
 * ModelTelemetryHelper provides utilities for recording model telemetry.
 * 
 * <p>
 * This helper should be used when invoking models to automatically record
 * metrics like latency, token counts, and error rates.
 */
public class ModelTelemetryHelper {

  private static final Logger logger = LoggerFactory.getLogger(ModelTelemetryHelper.class);

  /**
   * Executes a model call with automatic telemetry recording.
   *
   * @param modelName
   *            the model name
   * @param featureName
   *            the feature/flow name
   * @param path
   *            the span path
   * @param request
   *            the model request
   * @param modelFn
   *            the function that executes the model
   * @return the model response
   * @throws GenkitException
   *             if model execution fails
   */
  public static ModelResponse runWithTelemetry(String modelName, String featureName, String path,
      ModelRequest request, ModelExecutor modelFn) throws GenkitException {
    long startTime = System.currentTimeMillis();
    String error = null;
    ModelResponse response = null;

    try {
      response = modelFn.execute(request);

      // Calculate usage statistics if not provided by the model
      if (response != null && response.getUsage() == null) {
        Usage calculatedUsage = calculateBasicUsage(request, response);
        response.setUsage(calculatedUsage);
      }

      // Set latency if not already set
      if (response != null && response.getLatencyMs() == null) {
        response.setLatencyMs(System.currentTimeMillis() - startTime);
      }

      return response;
    } catch (GenkitException e) {
      error = e.getClass().getSimpleName();
      throw e;
    } catch (Exception e) {
      error = e.getClass().getSimpleName();
      throw new GenkitException("Model execution failed: " + e.getMessage(), e);
    } finally {
      long latencyMs = System.currentTimeMillis() - startTime;

      // Record telemetry metrics
      try {
        GenerateTelemetry.getInstance().recordGenerateMetrics(modelName,
            featureName != null ? featureName : "generate", path != null ? path : "", response, latencyMs,
            error);
      } catch (Exception e) {
        logger.warn("Failed to record model telemetry: {}", e.getMessage());
      }
    }
  }

  /**
   * Calculates basic usage statistics from request and response.
   *
   * @param request
   *            the model request
   * @param response
   *            the model response
   * @return calculated usage statistics
   */
  public static Usage calculateBasicUsage(ModelRequest request, ModelResponse response) {
    Usage usage = new Usage();

    // Calculate input statistics
    int inputChars = 0;
    int inputImages = 0;

    if (request != null && request.getMessages() != null) {
      for (Message message : request.getMessages()) {
        if (message.getContent() != null) {
          for (Part part : message.getContent()) {
            if (part.getText() != null) {
              inputChars += part.getText().length();
            }
            if (part.getMedia() != null) {
              String contentType = part.getMedia().getContentType();
              if (contentType != null && contentType.startsWith("image/")) {
                inputImages++;
              }
            }
          }
        }
      }
    }

    // Calculate output statistics
    int outputChars = 0;
    int outputImages = 0;

    if (response != null && response.getMessage() != null) {
      Message outputMessage = response.getMessage();
      if (outputMessage.getContent() != null) {
        for (Part part : outputMessage.getContent()) {
          if (part.getText() != null) {
            outputChars += part.getText().length();
          }
          if (part.getMedia() != null) {
            String contentType = part.getMedia().getContentType();
            if (contentType != null && contentType.startsWith("image/")) {
              outputImages++;
            }
          }
        }
      }
    }

    usage.setInputCharacters(inputChars);
    usage.setOutputCharacters(outputChars);
    usage.setInputImages(inputImages > 0 ? inputImages : null);
    usage.setOutputImages(outputImages > 0 ? outputImages : null);

    return usage;
  }

  /**
   * Functional interface for model execution.
   */
  @FunctionalInterface
  public interface ModelExecutor {
    /**
     * Executes the model with the given request.
     *
     * @param request
     *            the model request
     * @return the model response
     * @throws GenkitException
     *             if execution fails
     */
    ModelResponse execute(ModelRequest request) throws GenkitException;
  }
}
