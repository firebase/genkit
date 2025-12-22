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

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * HTTP-based telemetry client that sends traces to the Genkit telemetry server.
 */
public class HttpTelemetryClient implements TelemetryClient {

  private static final Logger logger = LoggerFactory.getLogger(HttpTelemetryClient.class);
  private static final ObjectMapper objectMapper = new ObjectMapper();

  private final String serverUrl;
  private final HttpClient httpClient;

  /**
   * Creates a new HTTP telemetry client.
   *
   * @param serverUrl
   *            the URL of the telemetry server
   */
  public HttpTelemetryClient(String serverUrl) {
    this.serverUrl = serverUrl.endsWith("/") ? serverUrl.substring(0, serverUrl.length() - 1) : serverUrl;
    this.httpClient = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();
  }

  @Override
  public void save(TraceData trace) throws Exception {
    if (serverUrl == null || serverUrl.isEmpty()) {
      logger.debug("Telemetry server URL not configured, skipping trace export");
      return;
    }

    String json = objectMapper.writeValueAsString(trace);

    HttpRequest request = HttpRequest.newBuilder().uri(URI.create(serverUrl + "/api/traces"))
        .header("Content-Type", "application/json").header("Accept", "application/json")
        .POST(HttpRequest.BodyPublishers.ofString(json)).timeout(Duration.ofSeconds(30)).build();

    HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

    if (response.statusCode() != 200) {
      logger.warn("Failed to send trace to telemetry server: status={}, body={}", response.statusCode(),
          response.body());
      throw new RuntimeException("Failed to send trace: HTTP " + response.statusCode());
    }

    logger.debug("Trace sent to telemetry server: traceId={}", trace.getTraceId());
  }
}
