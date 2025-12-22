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

package com.google.genkit.plugins.jetty;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.*;

import org.eclipse.jetty.server.Handler;
import org.eclipse.jetty.server.Request;
import org.eclipse.jetty.server.Response;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.server.ServerConnector;
import org.eclipse.jetty.server.handler.ContextHandler;
import org.eclipse.jetty.server.handler.ContextHandlerCollection;
import org.eclipse.jetty.util.Callback;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.genkit.core.*;

/**
 * JettyPlugin provides HTTP endpoints for Genkit flows.
 *
 * <p>
 * This plugin exposes registered flows as HTTP endpoints, making it easy to
 * deploy Genkit applications as web services.
 *
 * <p>
 * Example usage:
 * 
 * <pre>{@code
 * Genkit genkit = Genkit.builder().plugin(new JettyPlugin(JettyPluginOptions.builder().port(8080).build())).build();
 * 
 * // Define your flows...
 * 
 * // Start the server and block (keeps application running)
 * genkit.start();
 * }</pre>
 */
public class JettyPlugin implements ServerPlugin {

  private static final Logger logger = LoggerFactory.getLogger(JettyPlugin.class);

  private final JettyPluginOptions options;
  private Server server;
  private Registry registry;
  private ObjectMapper objectMapper;

  /**
   * Creates a JettyPlugin with default options.
   */
  public JettyPlugin() {
    this(JettyPluginOptions.builder().build());
  }

  /**
   * Creates a JettyPlugin with the specified options.
   *
   * @param options
   *            the plugin options
   */
  public JettyPlugin(JettyPluginOptions options) {
    this.options = options;
    this.objectMapper = new ObjectMapper();
  }

  /**
   * Creates a JettyPlugin with the specified port.
   *
   * @param port
   *            the HTTP port
   * @return a new JettyPlugin
   */
  public static JettyPlugin create(int port) {
    return new JettyPlugin(JettyPluginOptions.builder().port(port).build());
  }

  @Override
  public String getName() {
    return "jetty";
  }

  @Override
  public List<Action<?, ?, ?>> init() {
    // Jetty plugin doesn't provide actions itself
    return Collections.emptyList();
  }

  @Override
  public List<Action<?, ?, ?>> init(Registry registry) {
    this.registry = registry;
    return Collections.emptyList();
  }

  /**
   * Starts the Jetty server and blocks until it is stopped.
   * 
   * <p>
   * This is the recommended way to start the server in a main() method. Similar
   * to Express's app.listen() in JavaScript, this method will keep your
   * application running until the server is explicitly stopped.
   * 
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * JettyPlugin jetty = new JettyPlugin(JettyPluginOptions.builder().port(8080).build());
   * 
   * Genkit genkit = Genkit.builder().plugin(jetty).build();
   * 
   * // Define your flows...
   * 
   * // Start and block
   * jetty.start();
   * }</pre>
   *
   * @throws Exception
   *             if the server cannot be started or if interrupted while waiting
   */
  @Override
  public void start() throws Exception {
    if (registry == null) {
      throw new GenkitException(
          "Registry not set. Make sure JettyPlugin is added to Genkit before calling start().");
    }

    startServer();
    server.join();
  }

  /**
   * Starts the Jetty server without blocking.
   *
   * @throws Exception
   *             if the server cannot be started
   */
  private void startServer() throws Exception {
    if (server != null) {
      return;
    }

    if (registry == null) {
      throw new GenkitException(
          "Registry not set. Make sure JettyPlugin is added to Genkit before calling start().");
    }

    server = new Server();

    ServerConnector connector = new ServerConnector(server);
    connector.setPort(options.getPort());
    connector.setHost(options.getHost());
    server.addConnector(connector);

    // Create handler collection
    ContextHandlerCollection handlers = new ContextHandlerCollection();

    // Add flow endpoints
    addFlowHandlers(handlers);

    // Add health endpoint
    ContextHandler healthHandler = new ContextHandler("/health");
    healthHandler.setHandler(new HealthHandler());
    handlers.addHandler(healthHandler);

    server.setHandler(handlers);
    server.start();

    logger.info("Jetty server started on {}:{}", options.getHost(), options.getPort());
  }

  /**
   * Stops the Jetty server.
   *
   * @throws Exception
   *             if the server cannot be stopped
   */
  @Override
  public void stop() throws Exception {
    if (server != null) {
      server.stop();
      server = null;
      logger.info("Jetty server stopped");
    }
  }

  /**
   * Returns the port the server is listening on.
   *
   * @return the configured port
   */
  @Override
  public int getPort() {
    return options.getPort();
  }

  /**
   * Returns true if the server is currently running.
   *
   * @return true if the server is running, false otherwise
   */
  @Override
  public boolean isRunning() {
    return server != null && server.isRunning();
  }

  /**
   * Adds HTTP handlers for all registered flows.
   */
  private void addFlowHandlers(ContextHandlerCollection handlers) {
    List<Action<?, ?, ?>> flows = registry.listActions(ActionType.FLOW);

    for (Action<?, ?, ?> action : flows) {
      String path = options.getBasePath() + "/" + action.getName();

      ContextHandler handler = new ContextHandler(path);
      handler.setAllowNullPathInContext(true);
      handler.setHandler(new FlowHandler(action));
      handlers.addHandler(handler);

      logger.info("Registered flow endpoint: {}", path);
    }
  }

  /**
   * Handler for health check endpoint.
   */
  private class HealthHandler extends Handler.Abstract {
    @Override
    public boolean handle(Request request, Response response, Callback callback) throws Exception {
      response.setStatus(200);
      response.getHeaders().put("Content-Type", "application/json");

      String json = "{\"status\":\"ok\"}";
      response.write(true, ByteBuffer.wrap(json.getBytes(StandardCharsets.UTF_8)), callback);

      return true;
    }
  }

  /**
   * Handler for flow endpoints.
   */
  private class FlowHandler extends Handler.Abstract {
    private final Action<Object, Object, Object> action;

    @SuppressWarnings("unchecked")
    FlowHandler(Action<?, ?, ?> action) {
      this.action = (Action<Object, Object, Object>) action;
    }

    @Override
    public boolean handle(Request request, Response response, Callback callback) throws Exception {
      try {
        // Only accept POST requests
        if (!"POST".equals(request.getMethod())) {
          response.setStatus(405);
          response.getHeaders().put("Content-Type", "application/json");
          String error = "{\"error\":\"Method not allowed\"}";
          response.write(true, ByteBuffer.wrap(error.getBytes(StandardCharsets.UTF_8)), callback);
          return true;
        }

        // Read request body
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        Request.asInputStream(request).transferTo(baos);
        String body = baos.toString(StandardCharsets.UTF_8);

        // Parse input
        Object input = null;
        if (body != null && !body.isEmpty()) {
          input = objectMapper.readValue(body, Object.class);
        }

        // Run the action
        ActionContext context = new ActionContext(registry);
        Object result = action.run(context, input);

        // Send response
        response.setStatus(200);
        response.getHeaders().put("Content-Type", "application/json");

        String json = objectMapper.writeValueAsString(result);
        response.write(true, ByteBuffer.wrap(json.getBytes(StandardCharsets.UTF_8)), callback);

        return true;
      } catch (Exception e) {
        logger.error("Error handling flow request", e);

        response.setStatus(500);
        response.getHeaders().put("Content-Type", "application/json");

        // Format error with structured error status for proper UI display
        // For HTTP 500, send error status directly (no wrapper)
        // Format: {code, message, details: {stack}}
        String errorMessage = e.getMessage() != null ? e.getMessage() : "Unknown error";
        java.io.StringWriter sw = new java.io.StringWriter();
        e.printStackTrace(new java.io.PrintWriter(sw));
        String stacktrace = sw.toString();

        Map<String, Object> errorDetails = Map.of("stack", stacktrace);
        Map<String, Object> errorStatus = Map.of("code", 2, // INTERNAL error code
            "message", errorMessage, "details", errorDetails);

        String json = objectMapper.writeValueAsString(errorStatus);
        response.write(true, ByteBuffer.wrap(json.getBytes(StandardCharsets.UTF_8)), callback);

        return true;
      }
    }
  }
}
