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
import { describe, it } from 'node:test';
import { Document } from '../../src/document.js';

describe('document', () => {
  describe('text()', () => {
    it('retuns single text part', () => {
      const doc = new Document({ content: [{ text: 'foo' }] });

      assert.equal(doc.text(), 'foo');
    });

    it('retuns concatenated text part', () => {
      const doc = new Document({ content: [{ text: 'foo' }, { text: 'bar' }] });

      assert.equal(doc.text(), 'foobar');
    });
  });

  describe('media()', () => {
    it('retuns first media part', () => {
      const doc = new Document({
        content: [
          { media: { url: 'data:foo' } },
          { media: { url: 'data:bar' } },
        ],
      });

      assert.deepEqual(doc.media(), { url: 'data:foo' });
    });
  });

  describe('toJSON()', () => {
    it('retuns data object', () => {
      const doc = new Document({
        content: [{ text: 'foo' }],
        metadata: { bar: 'baz' },
      });

      assert.deepEqual(doc.toJSON(), {
        content: [{ text: 'foo' }],
        metadata: { bar: 'baz' },
      });
    });
  });

  describe('fromText()', () => {
    it('retuns data object', () => {
      const doc = Document.fromText('foo', { bar: 'baz' });

      assert.deepEqual(doc.toJSON(), {
        content: [{ text: 'foo' }],
        metadata: { bar: 'baz' },
      });
    });
  });
});
