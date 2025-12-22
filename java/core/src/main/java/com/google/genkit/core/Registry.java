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
import java.util.Map;

/**
 * Registry holds all registered actions and associated types, and provides
 * methods to register, query, and look up actions.
 *
 * <p>
 * The Registry is the central component for managing Genkit primitives. It
 * provides:
 * <ul>
 * <li>Storage and lookup of actions by key</li>
 * <li>Plugin management</li>
 * <li>Value storage for configuration</li>
 * <li>Schema registration for JSON validation</li>
 * <li>Hierarchical registry support for scoped operations</li>
 * </ul>
 */
public interface Registry {

  /**
   * Creates a new child registry that inherits from this registry. Child
   * registries are useful for scoped operations and will fall back to the parent
   * for lookups if a value is not found in the child.
   *
   * @return a new child registry
   */
  Registry newChild();

  /**
   * Returns true if this registry is a child of another registry.
   *
   * @return true if this is a child registry
   */
  boolean isChild();

  /**
   * Records the plugin in the registry.
   *
   * @param name
   *            the plugin name
   * @param plugin
   *            the plugin to register
   * @throws IllegalStateException
   *             if a plugin with the same name is already registered
   */
  void registerPlugin(String name, Plugin plugin);

  /**
   * Records the action in the registry.
   *
   * @param key
   *            the action key (type + name)
   * @param action
   *            the action to register
   * @throws IllegalStateException
   *             if an action with the same key is already registered
   */
  void registerAction(String key, Action<?, ?, ?> action);

  /**
   * Records an arbitrary value in the registry.
   *
   * @param name
   *            the value name
   * @param value
   *            the value to register
   * @throws IllegalStateException
   *             if a value with the same name is already registered
   */
  void registerValue(String name, Object value);

  /**
   * Records a JSON schema in the registry.
   *
   * @param name
   *            the schema name
   * @param schema
   *            the schema as a map
   * @throws IllegalStateException
   *             if a schema with the same name is already registered
   */
  void registerSchema(String name, Map<String, Object> schema);

  /**
   * Returns the plugin for the given name. It first checks the current registry,
   * then falls back to the parent if not found.
   *
   * @param name
   *            the plugin name
   * @return the plugin, or null if not found
   */
  Plugin lookupPlugin(String name);

  /**
   * Returns the action for the given key. It first checks the current registry,
   * then falls back to the parent if not found.
   *
   * @param key
   *            the action key
   * @return the action, or null if not found
   */
  Action<?, ?, ?> lookupAction(String key);

  /**
   * Returns the action for the given type and name.
   *
   * @param type
   *            the action type
   * @param name
   *            the action name
   * @return the action, or null if not found
   */
  default Action<?, ?, ?> lookupAction(ActionType type, String name) {
    return lookupAction(type.keyFromName(name));
  }

  /**
   * Returns the value for the given name. It first checks the current registry,
   * then falls back to the parent if not found.
   *
   * @param name
   *            the value name
   * @return the value, or null if not found
   */
  Object lookupValue(String name);

  /**
   * Returns a JSON schema for the given name. It first checks the current
   * registry, then falls back to the parent if not found.
   *
   * @param name
   *            the schema name
   * @return the schema as a map, or null if not found
   */
  Map<String, Object> lookupSchema(String name);

  /**
   * Looks up an action by key. If the action is not found, it attempts dynamic
   * resolution through registered dynamic plugins.
   *
   * @param key
   *            the action key
   * @return the action if found, or null if not found
   */
  Action<?, ?, ?> resolveAction(String key);

  /**
   * Looks up an action by type and name with dynamic resolution support.
   *
   * @param type
   *            the action type
   * @param name
   *            the action name
   * @return the action if found, or null if not found
   */
  default Action<?, ?, ?> resolveAction(ActionType type, String name) {
    return resolveAction(type.keyFromName(name));
  }

  /**
   * Returns a list of all registered actions. This includes actions from both the
   * current registry and its parent hierarchy.
   *
   * @return list of all registered actions
   */
  List<Action<?, ?, ?>> listActions();

  /**
   * Returns a list of all registered actions of the specified type.
   *
   * @param type
   *            the action type to filter by
   * @return list of actions of the specified type
   */
  List<Action<?, ?, ?>> listActions(ActionType type);

  /**
   * Registers an action by type and action name.
   *
   * @param type
   *            the action type
   * @param action
   *            the action to register
   */
  default void registerAction(ActionType type, Action<?, ?, ?> action) {
    registerAction(type.keyFromName(action.getName()), action);
  }

  /**
   * Returns a list of all registered plugins.
   *
   * @return list of all registered plugins
   */
  List<Plugin> listPlugins();

  /**
   * Returns a map of all registered values.
   *
   * @return map of all registered values
   */
  Map<String, Object> listValues();

  /**
   * Registers a partial template for use with prompts.
   *
   * @param name
   *            the partial name
   * @param source
   *            the partial template source
   */
  void registerPartial(String name, String source);

  /**
   * Registers a helper function for use with prompts.
   *
   * @param name
   *            the helper name
   * @param helper
   *            the helper function
   */
  void registerHelper(String name, Object helper);

  /**
   * Returns a registered partial by name.
   *
   * @param name
   *            the partial name
   * @return the partial source, or null if not found
   */
  String lookupPartial(String name);

  /**
   * Returns a registered helper by name.
   *
   * @param name
   *            the helper name
   * @return the helper function, or null if not found
   */
  Object lookupHelper(String name);
}
