/**
 * Copyright 2024 Google LLC
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
 */

import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { action } from '../src/action.js';
import { Registry } from '../src/registry.js';

describe('registry class', () => {
  var registry: Registry;
  beforeEach(() => {
    registry = new Registry();
  });

  describe('listActions', () => {
    it('returns all registered actions', async () => {
      const fooSomethingAction = action(
        { name: 'foo_something' },
        async () => null
      );
      registry.registerAction('model', fooSomethingAction);
      const barSomethingAction = action(
        { name: 'bar_something' },
        async () => null
      );
      registry.registerAction('model', barSomethingAction);

      assert.deepEqual(await registry.listActions(), {
        '/model/foo_something': fooSomethingAction,
        '/model/bar_something': barSomethingAction,
      });
    });

    it('returns all registered actions by plugins', async () => {
      registry.registerPluginProvider('foo', {
        name: 'foo',
        async initializer() {
          registry.registerAction('model', fooSomethingAction);
          return {};
        },
      });
      const fooSomethingAction = action(
        {
          name: {
            pluginId: 'foo',
            actionId: 'something',
          },
        },
        async () => null
      );
      registry.registerPluginProvider('bar', {
        name: 'bar',
        async initializer() {
          registry.registerAction('model', barSomethingAction);
          return {};
        },
      });
      const barSomethingAction = action(
        {
          name: {
            pluginId: 'bar',
            actionId: 'something',
          },
        },
        async () => null
      );

      assert.deepEqual(await registry.listActions(), {
        '/model/foo/something': fooSomethingAction,
        '/model/bar/something': barSomethingAction,
      });
    });

    it('returns all registered actions, including parent', async () => {
      const child = Registry.withParent(registry);

      const fooSomethingAction = action(
        { name: 'foo_something' },
        async () => null
      );
      registry.registerAction('model', fooSomethingAction);
      const barSomethingAction = action(
        { name: 'bar_something' },
        async () => null
      );
      child.registerAction('model', barSomethingAction);

      assert.deepEqual(await child.listActions(), {
        '/model/foo_something': fooSomethingAction,
        '/model/bar_something': barSomethingAction,
      });
      assert.deepEqual(await registry.listActions(), {
        '/model/foo_something': fooSomethingAction,
      });
    });
  });

  describe('lookupAction', () => {
    it('initializes plugin for action first', async () => {
      let fooInitialized = false;
      registry.registerPluginProvider('foo', {
        name: 'foo',
        async initializer() {
          fooInitialized = true;
          return {};
        },
      });
      let barInitialized = false;
      registry.registerPluginProvider('bar', {
        name: 'bar',
        async initializer() {
          barInitialized = true;
          return {};
        },
      });

      await registry.lookupAction('/model/foo/something');

      assert.strictEqual(fooInitialized, true);
      assert.strictEqual(barInitialized, false);

      await registry.lookupAction('/model/bar/something');

      assert.strictEqual(fooInitialized, true);
      assert.strictEqual(barInitialized, true);
    });

    it('returns registered action', async () => {
      const fooSomethingAction = action(
        { name: 'foo_something' },
        async () => null
      );
      registry.registerAction('model', fooSomethingAction);
      const barSomethingAction = action(
        { name: 'bar_something' },
        async () => null
      );
      registry.registerAction('model', barSomethingAction);

      assert.strictEqual(
        await registry.lookupAction('/model/foo_something'),
        fooSomethingAction
      );
      assert.strictEqual(
        await registry.lookupAction('/model/bar_something'),
        barSomethingAction
      );
    });

    it('returns action registered by plugin', async () => {
      registry.registerPluginProvider('foo', {
        name: 'foo',
        async initializer() {
          registry.registerAction('model', somethingAction);
          return {};
        },
      });
      const somethingAction = action(
        {
          name: {
            pluginId: 'foo',
            actionId: 'something',
          },
        },
        async () => null
      );

      assert.strictEqual(
        await registry.lookupAction('/model/foo/something'),
        somethingAction
      );
    });

    it('returns undefined for unknown action', async () => {
      assert.strictEqual(
        await registry.lookupAction('/model/foo/something'),
        undefined
      );
    });

    it('should lookup parent registry when child missing action', async () => {
      const childRegistry = new Registry(registry);

      const fooAction = action({ name: 'foo' }, async () => null);
      registry.registerAction('model', fooAction);

      assert.strictEqual(await registry.lookupAction('/model/foo'), fooAction);
      assert.strictEqual(
        await childRegistry.lookupAction('/model/foo'),
        fooAction
      );
    });

    it('registration on the child registry should not modify parent', async () => {
      const childRegistry = Registry.withParent(registry);

      assert.strictEqual(childRegistry.parent, registry);

      const fooAction = action({ name: 'foo' }, async () => null);
      childRegistry.registerAction('model', fooAction);

      assert.strictEqual(await registry.lookupAction('/model/foo'), undefined);
      assert.strictEqual(
        await childRegistry.lookupAction('/model/foo'),
        fooAction
      );
    });
  });
});
