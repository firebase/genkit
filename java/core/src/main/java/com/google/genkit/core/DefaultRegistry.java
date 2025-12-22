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

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * DefaultRegistry is the default implementation of the Registry interface. It
 * provides thread-safe storage and lookup of Genkit primitives.
 */
public class DefaultRegistry implements Registry {

  private static final Logger logger = LoggerFactory.getLogger(DefaultRegistry.class);

  private final Registry parent;
  private final Map<String, Action<?, ?, ?>> actions = new ConcurrentHashMap<>();
  private final Map<String, Plugin> plugins = new ConcurrentHashMap<>();
  private final Map<String, Object> values = new ConcurrentHashMap<>();
  private final Map<String, Map<String, Object>> schemas = new ConcurrentHashMap<>();
  private final Map<String, String> partials = new ConcurrentHashMap<>();
  private final Map<String, Object> helpers = new ConcurrentHashMap<>();

  /**
   * Creates a new root registry.
   */
  public DefaultRegistry() {
    this(null);
  }

  /**
   * Creates a new child registry with the given parent.
   *
   * @param parent
   *            the parent registry, or null for a root registry
   */
  public DefaultRegistry(Registry parent) {
    this.parent = parent;
  }

  @Override
  public Registry newChild() {
    return new DefaultRegistry(this);
  }

  @Override
  public boolean isChild() {
    return parent != null;
  }

  @Override
  public void registerPlugin(String name, Plugin plugin) {
    if (plugins.containsKey(name)) {
      throw new IllegalStateException("Plugin already registered: " + name);
    }
    plugins.put(name, plugin);
    logger.debug("Registered plugin: {}", name);
  }

  @Override
  public void registerAction(String key, Action<?, ?, ?> action) {
    if (actions.containsKey(key)) {
      throw new IllegalStateException("Action already registered: " + key);
    }
    actions.put(key, action);
    logger.debug("Registered action: {}", key);
  }

  @Override
  public void registerValue(String name, Object value) {
    if (values.containsKey(name)) {
      throw new IllegalStateException("Value already registered: " + name);
    }
    values.put(name, value);
    logger.debug("Registered value: {}", name);
  }

  @Override
  public void registerSchema(String name, Map<String, Object> schema) {
    if (schemas.containsKey(name)) {
      throw new IllegalStateException("Schema already registered: " + name);
    }
    schemas.put(name, schema);
    logger.debug("Registered schema: {}", name);
  }

  @Override
  public Plugin lookupPlugin(String name) {
    Plugin plugin = plugins.get(name);
    if (plugin == null && parent != null) {
      plugin = parent.lookupPlugin(name);
    }
    return plugin;
  }

  @Override
  public Action<?, ?, ?> lookupAction(String key) {
    Action<?, ?, ?> action = actions.get(key);
    if (action == null && parent != null) {
      action = parent.lookupAction(key);
    }
    return action;
  }

  @Override
  public Object lookupValue(String name) {
    Object value = values.get(name);
    if (value == null && parent != null) {
      value = parent.lookupValue(name);
    }
    return value;
  }

  @Override
  public Map<String, Object> lookupSchema(String name) {
    Map<String, Object> schema = schemas.get(name);
    if (schema == null && parent != null) {
      schema = parent.lookupSchema(name);
    }
    return schema;
  }

  @Override
  public Action<?, ?, ?> resolveAction(String key) {
    // First try direct lookup
    Action<?, ?, ?> action = lookupAction(key);
    if (action != null) {
      return action;
    }

    // Try dynamic resolution through plugins
    for (Plugin plugin : listPlugins()) {
      if (plugin instanceof DynamicPlugin) {
        DynamicPlugin dynamicPlugin = (DynamicPlugin) plugin;
        // Parse the key to get type and name
        String[] parts = key.split("/");
        if (parts.length >= 3) {
          ActionType type = ActionType.fromValue(parts[1]);
          String name = parts[2];
          action = dynamicPlugin.resolveAction(type, name);
          if (action != null) {
            // Register for future lookups
            registerAction(key, action);
            return action;
          }
        }
      }
    }

    return null;
  }

  @Override
  public List<Action<?, ?, ?>> listActions() {
    Map<String, Action<?, ?, ?>> allActions = new LinkedHashMap<>();

    // First add parent actions
    if (parent != null) {
      for (Action<?, ?, ?> action : parent.listActions()) {
        allActions.put(action.getDesc().getKey(), action);
      }
    }

    // Then add/override with local actions
    allActions.putAll(actions);

    // Also include dynamic actions from plugins
    for (Plugin plugin : listPlugins()) {
      if (plugin instanceof DynamicPlugin) {
        DynamicPlugin dynamicPlugin = (DynamicPlugin) plugin;
        for (ActionDesc desc : dynamicPlugin.listActions()) {
          if (!allActions.containsKey(desc.getKey())) {
            Action<?, ?, ?> action = dynamicPlugin.resolveAction(desc.getType(), desc.getName());
            if (action != null) {
              allActions.put(desc.getKey(), action);
            }
          }
        }
      }
    }

    return new ArrayList<>(allActions.values());
  }

  @Override
  public List<Action<?, ?, ?>> listActions(ActionType type) {
    String prefix = "/" + type.toString().toLowerCase() + "/";
    List<Action<?, ?, ?>> result = new ArrayList<>();

    for (Action<?, ?, ?> action : listActions()) {
      String key = action.getDesc() != null ? action.getDesc().getKey() : null;
      if (key != null && key.contains(prefix)) {
        result.add(action);
      } else {
        // Check by iterating through the local actions map
        for (Map.Entry<String, Action<?, ?, ?>> entry : actions.entrySet()) {
          if (entry.getKey().contains(prefix) && entry.getValue() == action) {
            result.add(action);
            break;
          }
        }
      }
    }

    return result;
  }

  @Override
  public List<Plugin> listPlugins() {
    Map<String, Plugin> allPlugins = new LinkedHashMap<>();

    // First add parent plugins
    if (parent != null) {
      for (Plugin plugin : parent.listPlugins()) {
        allPlugins.put(plugin.getName(), plugin);
      }
    }

    // Then add/override with local plugins
    allPlugins.putAll(plugins);

    return new ArrayList<>(allPlugins.values());
  }

  @Override
  public Map<String, Object> listValues() {
    Map<String, Object> allValues = new LinkedHashMap<>();

    // First add parent values
    if (parent != null) {
      allValues.putAll(parent.listValues());
    }

    // Then add/override with local values
    allValues.putAll(values);

    return allValues;
  }

  @Override
  public void registerPartial(String name, String source) {
    partials.put(name, source);
    logger.debug("Registered partial: {}", name);
  }

  @Override
  public void registerHelper(String name, Object helper) {
    helpers.put(name, helper);
    logger.debug("Registered helper: {}", name);
  }

  @Override
  public String lookupPartial(String name) {
    String partial = partials.get(name);
    if (partial == null && parent != null) {
      partial = parent.lookupPartial(name);
    }
    return partial;
  }

  @Override
  public Object lookupHelper(String name) {
    Object helper = helpers.get(name);
    if (helper == null && parent != null) {
      helper = parent.lookupHelper(name);
    }
    return helper;
  }
}
