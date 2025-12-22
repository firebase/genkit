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

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

/**
 * Unit tests for DefaultRegistry.
 */
@ExtendWith(MockitoExtension.class)
class DefaultRegistryTest {

  private DefaultRegistry registry;

  @Mock
  private Plugin mockPlugin;

  @Mock
  private Action<String, String, Void> mockAction;

  @BeforeEach
  void setUp() {
    registry = new DefaultRegistry();
  }

  @Test
  void testNewChild() {
    Registry child = registry.newChild();

    assertNotNull(child);
    assertTrue(child.isChild());
    assertFalse(registry.isChild());
  }

  @Test
  void testRegisterPlugin() {
    registry.registerPlugin("test-plugin", mockPlugin);

    Plugin result = registry.lookupPlugin("test-plugin");
    assertNotNull(result);
    assertEquals(mockPlugin, result);
  }

  @Test
  void testRegisterPluginDuplicate() {
    registry.registerPlugin("test-plugin", mockPlugin);

    assertThrows(IllegalStateException.class, () -> registry.registerPlugin("test-plugin", mockPlugin));
  }

  @Test
  void testRegisterAction() {
    String actionKey = "/flow/test-action";

    registry.registerAction(actionKey, mockAction);

    Action<?, ?, ?> result = registry.lookupAction(actionKey);
    assertNotNull(result);
    assertEquals(mockAction, result);
  }

  @Test
  void testRegisterActionDuplicate() {
    String actionKey = "/flow/test-action";
    registry.registerAction(actionKey, mockAction);

    assertThrows(IllegalStateException.class, () -> registry.registerAction(actionKey, mockAction));
  }

  @Test
  void testRegisterValue() {
    String valueName = "test-value";
    Object value = "test-object";

    registry.registerValue(valueName, value);

    Object result = registry.lookupValue(valueName);
    assertNotNull(result);
    assertEquals(value, result);
  }

  @Test
  void testRegisterValueDuplicate() {
    String valueName = "test-value";
    registry.registerValue(valueName, "value1");

    assertThrows(IllegalStateException.class, () -> registry.registerValue(valueName, "value2"));
  }

  @Test
  void testRegisterSchema() {
    String schemaName = "test-schema";
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "object");

    registry.registerSchema(schemaName, schema);

    Map<String, Object> result = registry.lookupSchema(schemaName);
    assertNotNull(result);
    assertEquals(schema, result);
  }

  @Test
  void testRegisterSchemaDuplicate() {
    String schemaName = "test-schema";
    Map<String, Object> schema = new HashMap<>();
    registry.registerSchema(schemaName, schema);

    assertThrows(IllegalStateException.class, () -> registry.registerSchema(schemaName, new HashMap<>()));
  }

  @Test
  void testChildRegistryLookupFromParent() {
    String actionKey = "/flow/parent-action";
    registry.registerAction(actionKey, mockAction);

    Registry child = registry.newChild();

    Action<?, ?, ?> result = child.lookupAction(actionKey);
    assertNotNull(result);
    assertEquals(mockAction, result);
  }

  @Test
  void testChildRegistryOverridesParent() {
    String actionKey = "/flow/test-action";

    @SuppressWarnings("unchecked")
    Action<String, String, Void> childAction = mock(Action.class);

    registry.registerAction(actionKey, mockAction);
    Registry child = registry.newChild();
    child.registerAction(actionKey + "-child", childAction);

    // Child can access parent action
    Action<?, ?, ?> parentResult = child.lookupAction(actionKey);
    assertNotNull(parentResult);
    assertEquals(mockAction, parentResult);

    // Child has its own action
    Action<?, ?, ?> childResult = child.lookupAction(actionKey + "-child");
    assertNotNull(childResult);
    assertEquals(childAction, childResult);
  }

  @Test
  void testLookupNonExistentPlugin() {
    Plugin result = registry.lookupPlugin("non-existent");
    assertNull(result);
  }

  @Test
  void testLookupNonExistentAction() {
    Action<?, ?, ?> result = registry.lookupAction("/flow/non-existent");
    assertNull(result);
  }

  @Test
  void testLookupNonExistentValue() {
    Object result = registry.lookupValue("non-existent");
    assertNull(result);
  }

  @Test
  void testLookupNonExistentSchema() {
    Map<String, Object> result = registry.lookupSchema("non-existent");
    assertNull(result);
  }

  @Test
  void testListPlugins() {
    @SuppressWarnings("unchecked")
    Plugin plugin2 = mock(Plugin.class);

    registry.registerPlugin("plugin1", mockPlugin);
    registry.registerPlugin("plugin2", plugin2);

    List<Plugin> plugins = registry.listPlugins();

    assertEquals(2, plugins.size());
    assertTrue(plugins.contains(mockPlugin));
    assertTrue(plugins.contains(plugin2));
  }

  @Test
  void testListActions() {
    registry.registerAction("/flow/action1", mockAction);

    List<Action<?, ?, ?>> actions = registry.listActions();

    assertEquals(1, actions.size());
    assertTrue(actions.contains(mockAction));
  }

  @Test
  void testListValues() {
    registry.registerValue("value1", "object1");
    registry.registerValue("value2", "object2");

    Map<String, Object> values = registry.listValues();

    assertEquals(2, values.size());
    assertEquals("object1", values.get("value1"));
    assertEquals("object2", values.get("value2"));
  }

  @Test
  void testRegisterPartial() {
    String partialName = "myPartial";
    String partialSource = "{{#each items}}{{this}}{{/each}}";

    registry.registerPartial(partialName, partialSource);

    String result = registry.lookupPartial(partialName);
    assertEquals(partialSource, result);
  }

  @Test
  void testRegisterHelper() {
    String helperName = "myHelper";
    Object helper = new Object();

    registry.registerHelper(helperName, helper);

    Object result = registry.lookupHelper(helperName);
    assertEquals(helper, result);
  }

  @Test
  void testChildLookupPartialFromParent() {
    String partialName = "parentPartial";
    String partialSource = "parent template";

    registry.registerPartial(partialName, partialSource);
    Registry child = registry.newChild();

    String result = child.lookupPartial(partialName);
    assertEquals(partialSource, result);
  }

  @Test
  void testChildLookupHelperFromParent() {
    String helperName = "parentHelper";
    Object helper = new Object();

    registry.registerHelper(helperName, helper);
    Registry child = registry.newChild();

    Object result = child.lookupHelper(helperName);
    assertEquals(helper, result);
  }
}
