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

package com.google.genkit;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.eclipse.jetty.server.Handler;
import org.eclipse.jetty.server.Request;
import org.eclipse.jetty.server.Response;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.server.ServerConnector;
import org.eclipse.jetty.util.Callback;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.google.genkit.ai.evaluation.*;
import com.google.genkit.core.Action;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.ActionDesc;
import com.google.genkit.core.ActionRunResult;
import com.google.genkit.core.GenkitException;
import com.google.genkit.core.JsonUtils;
import com.google.genkit.core.Registry;
import com.google.genkit.core.tracing.Tracer;

/**
 * ReflectionServer provides an HTTP API for the Genkit Developer UI to interact
 * with.
 * 
 * It exposes endpoints for listing actions, running actions, querying traces,
 * and evaluation.
 */
public class ReflectionServer {

  private static final Logger logger = LoggerFactory.getLogger(ReflectionServer.class);

  private final Registry registry;
  private final int port;
  private Server server;
  private String runtimeId;
  private EvaluationManager evaluationManager;

  /**
   * Creates a new ReflectionServer.
   *
   * @param registry
   *            the Genkit registry
   * @param port
   *            the port to listen on
   */
  public ReflectionServer(Registry registry, int port) {
    this.registry = registry;
    this.port = port;
    this.runtimeId = "java-" + ProcessHandle.current().pid() + "-" + System.currentTimeMillis();
    this.evaluationManager = new EvaluationManager(registry);
  }

  /**
   * Gets the runtime ID.
   */
  public String getRuntimeId() {
    return runtimeId;
  }

  /**
   * Starts the reflection server.
   *
   * @throws Exception
   *             if the server fails to start
   */
  public void start() throws Exception {
    server = new Server();

    // Configure connector with extended idle timeout for long-running operations
    // (e.g., video generation can take several minutes)
    ServerConnector connector = new ServerConnector(server);
    connector.setPort(port);
    connector.setIdleTimeout(900000); // 15 minutes idle timeout
    server.addConnector(connector);

    server.setHandler(new ReflectionHandler());
    server.start();
    logger.info("Reflection server started on port {}", port);
  }

  /**
   * Stops the reflection server.
   *
   * @throws Exception
   *             if the server fails to stop
   */
  public void stop() throws Exception {
    if (server != null) {
      server.stop();
      logger.info("Reflection server stopped");
    }
  }

  /**
   * Handler for reflection API requests using Jetty 12 Handler.Abstract.
   */
  private class ReflectionHandler extends Handler.Abstract {

    @Override
    public boolean handle(Request request, Response response, Callback callback) throws Exception {
      String target = request.getHttpURI().getPath();
      String method = request.getMethod();

      // Enable CORS
      response.getHeaders().add("Access-Control-Allow-Origin", "*");
      response.getHeaders().add("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
      response.getHeaders().add("Access-Control-Allow-Headers", "Content-Type, Accept");

      if ("OPTIONS".equals(method)) {
        response.setStatus(200);
        callback.succeeded();
        return true;
      }

      // Handle health check separately (no JSON content type needed)
      if ("/api/__health".equals(target)) {
        String query = request.getHttpURI().getQuery();
        String idParam = null;
        if (query != null) {
          for (String param : query.split("&")) {
            if (param.startsWith("id=")) {
              idParam = param.substring(3);
              break;
            }
          }
        }
        // If ID is provided, it must match our runtime ID
        if (idParam != null && !idParam.equals(runtimeId)) {
          response.setStatus(503);
          callback.succeeded();
          return true;
        }
        response.setStatus(200);
        callback.succeeded();
        return true;
      }

      response.getHeaders().add("Content-Type", "application/json");

      try {
        String result;
        int status = 200;

        if ("/api/actions".equals(target)) {
          result = handleListActions();
        } else if (target.startsWith("/api/actions/")) {
          String actionKey = target.substring("/api/actions/".length());
          result = handleGetAction(actionKey);
        } else if ("/api/runAction".equals(target)) {
          String body = readRequestBody(request);
          result = handleRunAction(body);
        } else if ("/api/notify".equals(target) && "POST".equals(method)) {
          String body = readRequestBody(request);
          result = handleNotify(body);
        } else if (target.startsWith("/api/envs/") && target.contains("/traces")) {
          result = handleListTraces();
        }
        // Dataset endpoints
        else if ("/api/datasets".equals(target) && "GET".equals(method)) {
          result = handleListDatasets();
        } else if ("/api/datasets".equals(target) && "POST".equals(method)) {
          String body = readRequestBody(request);
          result = handleCreateDataset(body);
        } else if (target.startsWith("/api/datasets/") && "GET".equals(method)) {
          String datasetId = target.substring("/api/datasets/".length());
          result = handleGetDataset(datasetId);
        } else if (target.startsWith("/api/datasets/") && "PUT".equals(method)) {
          String body = readRequestBody(request);
          result = handleUpdateDataset(body);
        } else if (target.startsWith("/api/datasets/") && "DELETE".equals(method)) {
          String datasetId = target.substring("/api/datasets/".length());
          result = handleDeleteDataset(datasetId);
        }
        // Evaluation endpoints
        else if ("/api/evalRuns".equals(target) && "GET".equals(method)) {
          result = handleListEvalRuns();
        } else if (target.startsWith("/api/evalRuns/") && "GET".equals(method)) {
          String evalRunId = target.substring("/api/evalRuns/".length());
          result = handleGetEvalRun(evalRunId);
        } else if (target.startsWith("/api/evalRuns/") && "DELETE".equals(method)) {
          String evalRunId = target.substring("/api/evalRuns/".length());
          result = handleDeleteEvalRun(evalRunId);
        } else if ("/api/runEvaluation".equals(target) && "POST".equals(method)) {
          String body = readRequestBody(request);
          result = handleRunEvaluation(body);
        } else {
          status = 404;
          result = createErrorResponse(5, "Not found", null); // NOT_FOUND code = 5
        }

        response.setStatus(status);
        byte[] bytes = result.getBytes(StandardCharsets.UTF_8);
        response.write(true, ByteBuffer.wrap(bytes), callback);

      } catch (Exception e) {
        logger.error("Error handling request", e);
        response.setStatus(500);
        String errorMessage = e.getMessage() != null ? e.getMessage() : "Unknown error";
        String stacktrace = getStackTraceString(e);
        // For HTTP 500 errors, send error status directly (no wrapper)
        String errorJson = createErrorStatus(2, errorMessage, stacktrace); // INTERNAL error code = 2
        byte[] bytes = errorJson.getBytes(StandardCharsets.UTF_8);
        response.write(true, ByteBuffer.wrap(bytes), callback);
      }

      return true;
    }

    private String getStackTraceString(Throwable e) {
      java.io.StringWriter sw = new java.io.StringWriter();
      e.printStackTrace(new java.io.PrintWriter(sw));
      return sw.toString();
    }

    /**
     * Creates a structured error status JSON string (without wrapper). Format:
     * {code, message, details: {stack}} Used for HTTP 500 error responses where the
     * body IS the error.
     */
    private String createErrorStatus(int code, String message, String stack) {
      Map<String, Object> errorDetails = new HashMap<>();
      if (stack != null) {
        errorDetails.put("stack", stack);
      }

      Map<String, Object> errorStatus = new HashMap<>();
      errorStatus.put("code", code);
      errorStatus.put("message", message);
      errorStatus.put("details", errorDetails);

      return JsonUtils.toJson(errorStatus);
    }

    /**
     * Creates a wrapped error response JSON string. Format: {error: {code, message,
     * details: {stack}}} Used for inline errors in 200 OK responses (e.g., action
     * not found).
     */
    private String createErrorResponse(int code, String message, String stack) {
      Map<String, Object> errorDetails = new HashMap<>();
      if (stack != null) {
        errorDetails.put("stack", stack);
      }

      Map<String, Object> errorStatus = new HashMap<>();
      errorStatus.put("code", code);
      errorStatus.put("message", message);
      errorStatus.put("details", errorDetails);

      Map<String, Object> errorResponse = new HashMap<>();
      errorResponse.put("error", errorStatus);

      return JsonUtils.toJson(errorResponse);
    }

    private String readRequestBody(Request request) throws Exception {
      ByteArrayOutputStream baos = new ByteArrayOutputStream();
      InputStream is = Request.asInputStream(request);
      byte[] buffer = new byte[4096];
      int bytesRead;
      while ((bytesRead = is.read(buffer)) != -1) {
        baos.write(buffer, 0, bytesRead);
      }
      return baos.toString(StandardCharsets.UTF_8);
    }

    private String handleListActions() {
      List<Action<?, ?, ?>> actions = registry.listActions();

      // Return as object keyed by action key (not array)
      Map<String, Map<String, Object>> actionMap = new HashMap<>();

      for (Action<?, ?, ?> action : actions) {
        Map<String, Object> actionInfo = new HashMap<>();
        ActionDesc desc = action.getDesc();
        String key;
        if (desc != null) {
          key = desc.getKey();
          actionInfo.put("key", key);
          actionInfo.put("name", desc.getName());
          actionInfo.put("description", desc.getDescription());
          actionInfo.put("inputSchema", desc.getInputSchema());
          actionInfo.put("outputSchema", desc.getOutputSchema());
          actionInfo.put("metadata", desc.getMetadata());
        } else {
          key = action.getType().keyFromName(action.getName());
          actionInfo.put("key", key);
          actionInfo.put("name", action.getName());
        }
        actionMap.put(key, actionInfo);
      }

      return JsonUtils.toJson(actionMap);
    }

    private String handleGetAction(String actionKey) {
      Action<?, ?, ?> action = registry.lookupAction(actionKey);
      if (action == null) {
        return createErrorResponse(5, "Action not found: " + actionKey, null); // NOT_FOUND code = 5
      }

      Map<String, Object> actionInfo = new HashMap<>();
      ActionDesc desc = action.getDesc();
      if (desc != null) {
        actionInfo.put("key", desc.getKey());
        actionInfo.put("name", desc.getName());
        actionInfo.put("description", desc.getDescription());
        actionInfo.put("inputSchema", desc.getInputSchema());
        actionInfo.put("outputSchema", desc.getOutputSchema());
        actionInfo.put("metadata", desc.getMetadata());
      } else {
        actionInfo.put("key", actionKey);
        actionInfo.put("name", action.getName());
      }

      return JsonUtils.toJson(actionInfo);
    }

    private String handleRunAction(String body) throws GenkitException {
      JsonNode requestNode = JsonUtils.parseJson(body);

      String key = requestNode.has("key") ? requestNode.get("key").asText() : null;
      JsonNode input = requestNode.has("input") ? requestNode.get("input") : null;

      if (key == null) {
        throw new GenkitException("Missing 'key' in request body");
      }

      Action<?, ?, ?> action = registry.lookupAction(key);
      if (action == null) {
        throw new GenkitException("Action not found: " + key);
      }

      ActionContext context = new ActionContext(registry);

      ActionRunResult<JsonNode> result = action.runJsonWithTelemetry(context, input, null);

      Map<String, Object> response = new HashMap<>();
      response.put("result", result.getResult());
      response.put("traceId", result.getTraceId());

      return JsonUtils.toJson(response);
    }

    private String handleListTraces() {
      // Return empty traces for now - this would need a proper trace store
      return "{\"traces\":[]}";
    }

    /**
     * Handle the notify endpoint from the Genkit CLI. This is used to receive
     * configuration like the telemetry server URL.
     */
    private String handleNotify(String body) {
      try {
        JsonNode requestNode = JsonUtils.parseJson(body);

        String telemetryServerUrl = requestNode.has("telemetryServerUrl")
            ? requestNode.get("telemetryServerUrl").asText()
            : null;
        int reflectionApiSpecVersion = requestNode.has("reflectionApiSpecVersion")
            ? requestNode.get("reflectionApiSpecVersion").asInt()
            : 0;

        if (telemetryServerUrl != null && !telemetryServerUrl.isEmpty()) {
          // Configure the telemetry exporter with the server URL
          Tracer.configureTelemetryServer(telemetryServerUrl);
        }

        // Warn if version mismatch
        if (reflectionApiSpecVersion != 0 && reflectionApiSpecVersion != 1) {
          logger.warn("Genkit CLI version may not be compatible with runtime library.");
        }

        return "\"OK\"";
      } catch (Exception e) {
        logger.error("Error handling notify request", e);
        String errorMessage = e.getMessage() != null ? e.getMessage() : "Unknown error";
        String stacktrace = getStackTraceString(e);
        return createErrorResponse(2, errorMessage, stacktrace); // INTERNAL error code = 2
      }
    }

    // =====================================================================
    // Dataset Endpoints
    // =====================================================================

    private String handleListDatasets() {
      try {
        List<DatasetMetadata> datasets = evaluationManager.getDatasetStore().listDatasets();
        return JsonUtils.toJson(datasets);
      } catch (Exception e) {
        logger.error("Error listing datasets", e);
        return createErrorResponse(2, e.getMessage(), getStackTraceString(e));
      }
    }

    private String handleGetDataset(String datasetId) {
      try {
        List<DatasetSample> dataset = evaluationManager.getDatasetStore().getDataset(datasetId);
        return JsonUtils.toJson(dataset);
      } catch (Exception e) {
        logger.error("Error getting dataset: {}", datasetId, e);
        return createErrorResponse(5, e.getMessage(), getStackTraceString(e));
      }
    }

    private String handleCreateDataset(String body) {
      try {
        CreateDatasetRequest request = JsonUtils.fromJson(body, CreateDatasetRequest.class);
        DatasetMetadata metadata = evaluationManager.getDatasetStore().createDataset(request);
        return JsonUtils.toJson(metadata);
      } catch (Exception e) {
        logger.error("Error creating dataset", e);
        return createErrorResponse(2, e.getMessage(), getStackTraceString(e));
      }
    }

    private String handleUpdateDataset(String body) {
      try {
        UpdateDatasetRequest request = JsonUtils.fromJson(body, UpdateDatasetRequest.class);
        DatasetMetadata metadata = evaluationManager.getDatasetStore().updateDataset(request);
        return JsonUtils.toJson(metadata);
      } catch (Exception e) {
        logger.error("Error updating dataset", e);
        return createErrorResponse(2, e.getMessage(), getStackTraceString(e));
      }
    }

    private String handleDeleteDataset(String datasetId) {
      try {
        evaluationManager.getDatasetStore().deleteDataset(datasetId);
        return "{}";
      } catch (Exception e) {
        logger.error("Error deleting dataset: {}", datasetId, e);
        return createErrorResponse(2, e.getMessage(), getStackTraceString(e));
      }
    }

    // =====================================================================
    // Evaluation Endpoints
    // =====================================================================

    private String handleListEvalRuns() {
      try {
        List<EvalRunKey> evalRuns = evaluationManager.getEvalStore().list();
        return JsonUtils.toJson(evalRuns);
      } catch (Exception e) {
        logger.error("Error listing eval runs", e);
        return createErrorResponse(2, e.getMessage(), getStackTraceString(e));
      }
    }

    private String handleGetEvalRun(String evalRunId) {
      try {
        EvalRun evalRun = evaluationManager.getEvalStore().load(evalRunId);
        if (evalRun == null) {
          return createErrorResponse(5, "Eval run not found: " + evalRunId, null);
        }
        return JsonUtils.toJson(evalRun);
      } catch (Exception e) {
        logger.error("Error getting eval run: {}", evalRunId, e);
        return createErrorResponse(2, e.getMessage(), getStackTraceString(e));
      }
    }

    private String handleDeleteEvalRun(String evalRunId) {
      try {
        evaluationManager.getEvalStore().delete(evalRunId);
        return "{}";
      } catch (Exception e) {
        logger.error("Error deleting eval run: {}", evalRunId, e);
        return createErrorResponse(2, e.getMessage(), getStackTraceString(e));
      }
    }

    private String handleRunEvaluation(String body) {
      try {
        RunEvaluationRequest request = JsonUtils.fromJson(body, RunEvaluationRequest.class);
        EvalRunKey evalRunKey = evaluationManager.runEvaluation(request);
        return JsonUtils.toJson(evalRunKey);
      } catch (Exception e) {
        logger.error("Error running evaluation", e);
        return createErrorResponse(2, e.getMessage(), getStackTraceString(e));
      }
    }
  }
}
