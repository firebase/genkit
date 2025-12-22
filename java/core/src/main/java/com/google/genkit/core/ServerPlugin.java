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

package com.google.genkit.core;

/**
 * ServerPlugin is an extended Plugin interface for plugins that provide HTTP
 * server functionality.
 * 
 * <p>
 * This interface adds lifecycle methods for starting and stopping servers. The
 * {@link #start()} method blocks until the server is stopped, similar to
 * Express's app.listen() in JavaScript.
 * 
 * <p>
 * Example usage:
 * 
 * <pre>{@code
 * JettyPlugin jetty = new JettyPlugin(JettyPluginOptions.builder().port(8080).build());
 * 
 * Genkit genkit = Genkit.builder().plugin(jetty).build();
 * 
 * // Define your flows here...
 * 
 * // Start the server and block - this replaces Thread.currentThread().join()
 * jetty.start();
 * }</pre>
 */
public interface ServerPlugin extends Plugin {

  /**
   * Starts the HTTP server and blocks until it is stopped.
   * 
   * <p>
   * This is the recommended way to start a server in a main() method. Similar to
   * Express's app.listen() in JavaScript, this method will keep your application
   * running until the server is explicitly stopped.
   *
   * @throws Exception
   *             if the server cannot be started or if interrupted while waiting
   */
  void start() throws Exception;

  /**
   * Stops the HTTP server.
   *
   * @throws Exception
   *             if the server cannot be stopped
   */
  void stop() throws Exception;

  /**
   * Returns the port the server is listening on.
   *
   * @return the server port
   */
  int getPort();

  /**
   * Returns true if the server is currently running.
   *
   * @return true if running, false otherwise
   */
  boolean isRunning();
}
