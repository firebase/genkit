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

import { Registry } from '@genkit-ai/core/registry';
import * as assert from 'assert';
import { beforeEach, describe, it } from 'node:test';
import { defineResource, findMatchingResource } from '../../src/resource.js';

describe('resource', () => {
  let registry: Registry;

  beforeEach(() => {
    registry = new Registry();
  });

  it('defines and matches static resource uri', async () => {
    const testResource = defineResource(
      registry,
      {
        name: 'testResource',
        uri: 'foo://bar',
        description: 'does foo things',
        metadata: { foo: 'bar' },
      },
      () => {
        return [{ text: 'foo stuff' }];
      }
    );

    assert.ok(testResource);
    assert.strictEqual(testResource.__action.description, 'does foo things');
    assert.deepStrictEqual(testResource.__action.metadata, {
      foo: 'bar',
      resource: {
        template: undefined,
        uri: 'foo://bar',
      },
    });

    assert.strictEqual(testResource.matches('foo://bar'), true);
    assert.strictEqual(testResource.matches('foo://baz'), false);

    assert.deepStrictEqual(await testResource('foo://bar'), [
      {
        text: 'foo stuff',
        metadata: {
          resource: {
            name: 'testResource',
            uri: 'foo://bar',
          },
        },
      },
    ]);

    assert.ok(await registry.lookupAction('/resource/testResource'));
  });

  it('defines and matches templates resource uri', async () => {
    const testResource = defineResource(
      registry,
      {
        name: 'testResource',
        template: 'foo://bar/{baz}',
        description: 'does foo things',
      },
      (input) => {
        return [{ text: `foo stuff ${input}` }];
      }
    );

    assert.ok(testResource);
    assert.strictEqual(testResource.__action.description, 'does foo things');

    assert.strictEqual(testResource.matches('foo://bar/something'), true);
    assert.strictEqual(testResource.matches('foo://baz/something'), false);

    assert.deepStrictEqual(await testResource('foo://bar/something'), [
      {
        text: 'foo stuff foo://bar/something',
        metadata: {
          resource: {
            name: 'testResource',
            uri: 'foo://bar/something',
          },
        },
      },
    ]);

    assert.ok(await registry.lookupAction('/resource/testResource'));
  });

  it('handle parent resources', async () => {
    const testResource = defineResource(
      registry,
      {
        name: 'testResource',
        template: 'file://{/id*}',
        description: 'does foo things',
      },
      (file) => {
        return [
          { text: `sub1`, metadata: { resource: { uri: `${file}/sub1.txt` } } },
          { text: `sub2`, metadata: { resource: { uri: `${file}/sub2.txt` } } },
        ];
      }
    );
    assert.strictEqual(testResource.matches('file:///some/directory'), true);

    assert.deepStrictEqual(await testResource('file:///some/directory'), [
      {
        text: 'sub1',
        metadata: {
          resource: {
            parent: {
              uri: 'file:///some/directory',
            },
            uri: 'file:///some/directory/sub1.txt',
          },
        },
      },
      {
        text: 'sub2',
        metadata: {
          resource: {
            parent: {
              uri: 'file:///some/directory',
            },
            uri: 'file:///some/directory/sub2.txt',
          },
        },
      },
    ]);
  });

  it('finds matching resource', async () => {
    defineResource(
      registry,
      {
        name: 'testTemplateResource',
        template: 'foo://bar/{baz}',
        description: 'does foo things',
      },
      (input) => {
        return [{ text: `foo stuff ${input}` }];
      }
    );
    defineResource(
      registry,
      {
        name: 'testResource',
        uri: 'bar://baz',
        description: 'does bar things',
      },
      () => {
        return [{ text: `bar` }];
      }
    );

    const gotBar = await findMatchingResource(registry, 'bar://baz');
    assert.ok(gotBar);
    assert.strictEqual(gotBar.__action.name, 'testResource');

    const gotFoo = await findMatchingResource(registry, 'foo://bar/something');
    assert.ok(gotFoo);
    assert.strictEqual(gotFoo.__action.name, 'testTemplateResource');
    assert.deepStrictEqual(gotFoo.__action.metadata, {
      resource: {
        template: 'foo://bar/{baz}',
        uri: undefined,
      },
    });

    const gotUnmatched = await findMatchingResource(
      registry,
      'unknown://bar/something'
    );
    assert.strictEqual(gotUnmatched, undefined);
  });
});
