import { describe, it, beforeEach } from 'node:test';
import {
  __hardResetRegistryForTesting,
  registerPluginProvider,
  registerAction,
  lookupAction,
  listActions,
} from '../src/registry';
import assert from 'node:assert';
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
      var fooInitialized = false;
      registerPluginProvider('foo', {
        name: 'foo',
        async initializer() {
          fooInitialized = true;
          return {};
        },
      });
      var barInitialized = false;
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
