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
import {
  listActions,
  lookupAction,
  registerAction,
  registerPluginProvider,
  __hardResetRegistryForTesting,
} from '../src/registry';
import { action } from '../src/types';

describe('registry', () => {
  beforeEach(__hardResetRegistryForTesting);

  describe('listActions', () => {
    it('returns all registered actions', async () => {
      const fooSomethingAction = action(
        { name: 'foo/something' },
        async () => null
      );
      registerAction('model', 'foo/something', fooSomethingAction);
      const barSomethingAction = action(
        { name: 'bar/something' },
        async () => null
      );
      registerAction('model', 'bar/something', barSomethingAction);

      assert.deepEqual(await listActions(), {
        '/model/foo/something': fooSomethingAction,
        '/model/bar/something': barSomethingAction,
      });
    });

    it('returns all registered actions by plugins', async () => {
      const fooSomethingAction = action(
        { name: 'foo/something' },
        async () => null
      );
      registerPluginProvider('foo', {
        name: 'foo',
        async initializer() {
          registerAction('model', 'foo/something', fooSomethingAction);
          return {};
        },
      });
      const barSomethingAction = action(
        { name: 'bar/something' },
        async () => null
      );
      registerPluginProvider('bar', {
        name: 'bar',
        async initializer() {
          registerAction('model', 'bar/something', barSomethingAction);
          return {};
        },
      });

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
      { name: 'foo/something' },
      async () => null
    );
    registerAction('model', 'foo/something', fooSomethingAction);
    const barSomethingAction = action(
      { name: 'bar/something' },
      async () => null
    );
    registerAction('model', 'bar/something', barSomethingAction);

    assert.strictEqual(
      await lookupAction('/model/foo/something'),
      fooSomethingAction
    );
    assert.strictEqual(
      await lookupAction('/model/bar/something'),
      barSomethingAction
    );
  });

  it('returns action registered by plugin', async () => {
    const somethingAction = action({ name: 'foo/something' }, async () => null);

    registerPluginProvider('foo', {
      name: 'foo',
      async initializer() {
        registerAction('model', 'foo/something', somethingAction);
        return {};
      },
    });

    assert.strictEqual(
      await lookupAction('/model/foo/something'),
      somethingAction
    );
  });

  it('returns undefined for unknown action', async () => {
    assert.strictEqual(await lookupAction('/model/foo/something'), undefined);
  });
});
