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

import * as assert from 'assert';
import { describe, it } from 'node:test';
import { Document, checkUniqueDocuments } from '../../src/document.js';
import { Embedding } from '../../src/embedder.js';

describe('document', () => {
  describe('constructor', () => {
    it('makes a copy, not a reference', () => {
      let content = [
        { media: { url: 'data:foo' } },
        { media: { url: 'data:bar' } },
      ];
      let metadata = { bar: 'baz', embedMetadata: { bar: 'qux' } };
      const doc = new Document({ content, metadata });

      // Change the deep parts of the content
      if (doc.content[0].media) {
        content[0].media.url = 'data: bam';
        assert.equal(doc.content[0].media.url, 'data:foo');
      } else {
        assert.fail('doc.content[0].media is not present');
      }

      // Change the deep parts of the metadata
      if (
        doc.metadata &&
        doc.metadata.embedMetadata &&
        doc.metadata.embedMetadata.bar
      ) {
        metadata.embedMetadata.bar = 'boom';
        assert.equal(doc.metadata.embedMetadata.bar, 'qux');
      } else {
        assert.fail('doc.metadata.embedMetadata.bar is not present');
      }
    });
  });

  describe('text()', () => {
    it('returns single text part', () => {
      const doc = new Document({ content: [{ text: 'foo' }] });

      assert.equal(doc.text, 'foo');
    });

    it('returns concatenated text part', () => {
      const doc = new Document({ content: [{ text: 'foo' }, { text: 'bar' }] });

      assert.equal(doc.text, 'foobar');
    });
  });

  describe('media()', () => {
    it('returns an array of media', () => {
      const doc = new Document({
        content: [
          { media: { url: 'data:foo' } },
          { media: { url: 'data:bar' } },
        ],
      });

      assert.deepEqual(doc.media, [{ url: 'data:foo' }, { url: 'data:bar' }]);
    });
  });

  describe('data()', () => {
    it('returns the text in a text document', () => {
      const doc = Document.fromText('foo');
      assert.equal(doc.data, 'foo');
    });

    it('returns the image in an image document', () => {
      const url = 'gs://somebucket/someimage.png';
      const doc = Document.fromMedia(url, 'image/png');
      assert.equal(doc.data, url);
    });

    it('returns the video in a video document', () => {
      const url = 'gs://somebucket/somevideo.mp4';
      const doc = Document.fromMedia(url, 'video/mp4');
      assert.equal(doc.data, url);
    });
  });

  describe('dataType()', () => {
    it('returns "text" for a text document', () => {
      const doc = Document.fromText('foo');
      assert.equal(doc.dataType, 'text');
    });

    it('returns the image type in an image document', () => {
      const contentType = 'image/png';
      const doc = Document.fromMedia(
        'gs://somebucket/someimage.png',
        contentType
      );
      assert.equal(doc.dataType, contentType);
    });

    it('returns the video type in a video document', () => {
      const contentType = 'video/mp4';
      const doc = Document.fromMedia(
        'gs://somebucket/somevideo.mp4',
        contentType
      );
      assert.equal(doc.dataType, contentType);
    });
  });

  describe('toJSON()', () => {
    it('returns data object', () => {
      const doc = new Document({
        content: [{ text: 'foo' }],
        metadata: { bar: 'baz', embedMetadata: { bar: 'qux' } },
      });

      assert.deepEqual(doc.toJSON(), {
        content: [{ text: 'foo' }],
        metadata: { bar: 'baz', embedMetadata: { bar: 'qux' } },
      });
    });

    it('makes a copy not a reference', () => {
      let content = [
        { media: { url: 'data:foo' } },
        { media: { url: 'data:bar' } },
      ];
      let metadata = { bar: 'baz', embedMetadata: { bar: 'qux' } };
      const doc = new Document({ content, metadata });

      const jsonDoc = doc.toJSON();
      assert.deepStrictEqual(jsonDoc.content, content);
      assert.deepStrictEqual(jsonDoc.metadata, metadata);

      // Change the deep parts of the content in the doc
      if (doc.content[0].media) {
        doc.content[0].media.url = 'data: bam';
        assert.equal(jsonDoc.content[0].media.url, 'data:foo');
      } else {
        assert.fail('doc.content[0].media is not present');
      }

      // Change the deep parts of the metadata in the doc
      if (
        doc.metadata &&
        doc.metadata.embedMetadata &&
        doc.metadata.embedMetadata.bar
      ) {
        doc.metadata.embedMetadata.bar = 'boom';
        assert.equal(jsonDoc.metadata.embedMetadata.bar, 'qux');
      } else {
        assert.fail('doc.metadata.embedMetadata.bar is not present');
      }
    });
  });

  describe('fromText()', () => {
    it('returns Document with text', () => {
      const doc = Document.fromText('foo', { bar: 'baz' });

      assert.deepEqual(doc.toJSON(), {
        content: [{ text: 'foo' }],
        metadata: { bar: 'baz' },
      });
    });
  });

  describe('fromMedia', () => {
    it('returns Document with image and metadata', () => {
      const url = 'gs://somebucket/someimage.jpg';
      const contentType = 'image/jpeg';
      const metadata = { embedMetadata: { embeddingType: 'image' } };
      const doc = Document.fromMedia(url, contentType, metadata);
      assert.deepEqual(doc.toJSON(), {
        content: [
          {
            media: {
              contentType,
              url,
            },
          },
        ],
        metadata,
      });
    });

    it('returns Document with video and metadata', () => {
      const url = 'gs://somebucket/somevideo.mp4';
      const contentType = 'video/mp4';
      const metadata = {
        start: 0,
        end: 120,
        embedMetadata: { embeddingType: 'video', start: 15, end: 30 },
      };
      const doc = Document.fromMedia(url, contentType, metadata);
      assert.deepEqual(doc.toJSON(), {
        content: [
          {
            media: {
              contentType,
              url,
            },
          },
        ],
        metadata,
      });
    });
  });

  describe('fromData', () => {
    it('returns a Document with text', () => {
      const data = 'foo';
      const dataType = 'text';
      const metadata = { embedMetadata: { embeddingType: 'text' } };
      const doc = Document.fromData(data, dataType, metadata);
      assert.deepEqual(doc.toJSON(), {
        content: [{ text: data }],
        metadata,
      });
    });

    it('returns a Document with image', () => {
      const data = 'iVBORw0KGgoAAAANSUhEUgAAAAjCB0C8AAAAASUVORK5CYII=';
      const dataType = 'image/png';
      const metadata = { embedMetadata: { embeddingType: 'image' } };
      const doc = Document.fromData(data, dataType, metadata);
      assert.deepEqual(doc.toJSON(), {
        content: [
          {
            media: {
              contentType: dataType,
              url: data,
            },
          },
        ],
        metadata,
      });
    });

    it('returns a Document with video', () => {
      const data = 'gs://somebucket/somevideo.mp4';
      const dataType = 'video/mp4';
      const metadata = {
        start: 0,
        end: 120,
        embedMetadata: { embeddingType: 'video', start: 15, end: 30 },
      };
      const doc = Document.fromData(data, dataType, metadata);
      assert.deepEqual(doc.toJSON(), {
        content: [
          {
            media: {
              contentType: dataType,
              url: data,
            },
          },
        ],
        metadata,
      });
    });
  });

  describe('getEmbeddingDocuments', () => {
    it('returns the same document for single embedding', () => {
      const doc = Document.fromText('foo');
      const embeddings: Embedding[] = [
        {
          embedding: [0.1, 0.2, 0.3],
        },
      ];
      const docs = doc.getEmbeddingDocuments(embeddings);
      assert.deepEqual(docs, [doc]);
    });

    it('returns an array of document for multiple embeddings', () => {
      const url = 'gs://somebucket/somevideo.mp4';
      const contentType = 'video/mp4';
      const metadata = { start: 0, end: 60 };
      const doc = Document.fromMedia(url, contentType, metadata);

      let embeddings: Embedding[] = [];
      for (var start = 0; start < 60; start += 15) {
        embeddings.push(makeTestEmbedding(start));
      }
      const docs = doc.getEmbeddingDocuments(embeddings);
      assert.equal(docs.length, embeddings.length);
      for (var i = 0; i < docs.length; i++) {
        assert.deepEqual(docs[i].toJSON().content, doc.toJSON().content);
        assert.deepEqual(
          docs[i].toJSON().metadata?.embedMetadata,
          embeddings[i].metadata
        );
        var origMetadata = JSON.parse(
          JSON.stringify(docs[i].metadata)
        ) as Record<string, unknown>;
        delete origMetadata.embedMetadata;
        assert.deepEqual(origMetadata, doc.toJSON().metadata);
      }
    });

    it('returns unique embedding documents', () => {
      const url = 'gs://somebucket/somevideo.mp4';
      const contentType = 'video/mp4';
      const metadata = { start: 0, end: 60 };
      const doc = Document.fromMedia(url, contentType, metadata);

      let embeddings: Embedding[] = [];
      for (var start = 0; start < 60; start += 15) {
        embeddings.push(makeTestEmbedding(start));
      }
      const docs = doc.getEmbeddingDocuments(embeddings);
      assert.equal(checkUniqueDocuments(docs), true);
    });
  });

  function makeTestEmbedding(start: number): Embedding {
    return {
      embedding: [0.1, 0.2, 0.3],
      metadata: {
        embeddingType: 'video',
        start: start,
        end: start + 15,
      },
    };
  }
});
