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

import java.util.List;

/**
 * Plugin is the interface implemented by types that extend Genkit's
 * functionality. Plugins are typically used to integrate external services like
 * model providers, vector databases, or monitoring tools.
 *
 * <p>
 * Plugins are registered and initialized via the Genkit builder during
 * initialization.
 */
public interface Plugin {

  /**
   * Returns the unique identifier for the plugin. This name is used for
   * registration and lookup.
   *
   * @return the plugin name
   */
  String getName();

  /**
   * Initializes the plugin. This method is called once during Genkit
   * initialization. The plugin should return a list of actions that it provides.
   *
   * @return list of actions provided by this plugin
   */
  List<Action<?, ?, ?>> init();

  /**
   * Initializes the plugin with access to the registry. This method is called
   * once during Genkit initialization. The plugin should return a list of actions
   * that it provides.
   *
   * <p>
   * Override this method instead of {@link #init()} when your plugin needs to
   * resolve dependencies from the registry (e.g., embedders, models).
   *
   * @param registry
   *            the Genkit registry for resolving dependencies
   * @return list of actions provided by this plugin
   */
  default List<Action<?, ?, ?>> init(Registry registry) {
    return init();
  }
}
