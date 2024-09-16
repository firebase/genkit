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
import {
  __hardResetRegistryForTesting,
  listActions,
  lookupAction,
  registerAction,
  registerPluginProvider,
} from '../src/registry.js';

describe('registry', () => {
  beforeEach(__hardResetRegistryForTesting);

  describe('listActions', () => {
    it('returns all registered actions', async () => {
      const fooSomethingAction = action(
        { name: 'foo_something' },
        async () => null
      );
      registerAction('model', fooSomethingAction);
      const barSomethingAction = action(
        { name: 'bar_something' },
        async () => null
      );
      registerAction('model', barSomethingAction);

      assert.deepEqual(await listActions(), {
        '/model/foo_something': fooSomethingAction,
        '/model/bar_something': barSomethingAction,
      });
    });

    it('returns all registered actions by plugins', async () => {
      registerPluginProvider('foo', {
        name: 'foo',
        async initializer() {
          registerAction('model', fooSomethingAction);
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
      registerPluginProvider('bar', {
        name: 'bar',
        async initializer() {
          registerAction('model', barSomethingAction);
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

      assert.deepEqual(await listActions(), {
        '/model/foo/something': fooSomethingAction,
        '/model/bar/something': barSomethingAction,
      });
    });
  });

  describe('lookupAction', () => {
    it('initializes plugin for action first', async () => {
      let fooInitialized = false;
      registerPluginProvider('foo', {
        name: 'foo',
        async initializer() {
          fooInitialized = true;
          return {};
        },
      });
      let barInitialized = false;
      registerPluginProvider('bar', {
        name: 'bar',
        async initializer() {
          barInitialized = true;
          return {};
        },
      });

      await lookupAction('/model/foo/something');

      assert.strictEqual(fooInitialized, true);
      assert.strictEqual(barInitialized, false);

      await lookupAction('/model/bar/something');

      assert.strictEqual(fooInitialized, true);
      assert.strictEqual(barInitialized, true);
    });
  });

  it('returns registered action', async () => {
    const fooSomethingAction = action(
      { name: 'foo_something' },
      async () => null
    );
    registerAction('model', fooSomethingAction);
    const barSomethingAction = action(
      { name: 'bar_something' },
      async () => null
    );
    registerAction('model', barSomethingAction);

    assert.strictEqual(
      await lookupAction('/model/foo_something'),
      fooSomethingAction
    );
    assert.strictEqual(
      await lookupAction('/model/bar_something'),
      barSomethingAction
    );
  });

  it('returns action registered by plugin', async () => {
    registerPluginProvider('foo', {
      name: 'foo',
      async initializer() {
        registerAction('model', somethingAction);
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
      await lookupAction('/model/foo/something'),
      somethingAction
    );
  });

  it('returns undefined for unknown action', async () => {
    assert.strictEqual(await lookupAction('/model/foo/something'), undefined);
  });
});
