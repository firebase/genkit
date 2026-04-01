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

import { Context, type Span } from '@opentelemetry/api';
import type {
  ReadableSpan,
  SpanProcessor,
} from '@opentelemetry/sdk-trace-base';
import * as assert from 'assert';
import { describe, it } from 'node:test';
import { MultiSpanProcessor } from '../src/tracing/node-telemetry-provider.js';

describe('MultiSpanProcessor', () => {
  it('should continue executing processors even if one throws in onStart', () => {
    let callCount = 0;
    const failingProcessor: SpanProcessor = {
      onStart: () => {
        throw new Error('Boom!');
      },
      onEnd: () => {},
      forceFlush: async () => {},
      shutdown: async () => {},
    };
    const succeedingProcessor: SpanProcessor = {
      onStart: () => {
        callCount++;
      },
      onEnd: () => {},
      forceFlush: async () => {},
      shutdown: async () => {},
    };

    const multi = new MultiSpanProcessor([
      failingProcessor,
      succeedingProcessor,
    ]);
    multi.onStart({} as Span, {} as Context);

    assert.strictEqual(callCount, 1);
  });

  it('should continue executing processors even if one throws in onEnd', () => {
    let callCount = 0;
    const failingProcessor: SpanProcessor = {
      onStart: () => {},
      onEnd: () => {
        throw new Error('Boom!');
      },
      forceFlush: async () => {},
      shutdown: async () => {},
    };
    const succeedingProcessor: SpanProcessor = {
      onStart: () => {},
      onEnd: () => {
        callCount++;
      },
      forceFlush: async () => {},
      shutdown: async () => {},
    };

    const multi = new MultiSpanProcessor([
      failingProcessor,
      succeedingProcessor,
    ]);
    multi.onEnd({} as ReadableSpan);

    assert.strictEqual(callCount, 1);
  });

  it('should continue executing processors even if one throws in forceFlush', async () => {
    let callCount = 0;
    const failingProcessor: SpanProcessor = {
      onStart: () => {},
      onEnd: () => {},
      forceFlush: async () => {
        throw new Error('Boom!');
      },
      shutdown: async () => {},
    };
    const succeedingProcessor: SpanProcessor = {
      onStart: () => {},
      onEnd: () => {},
      forceFlush: async () => {
        callCount++;
      },
      shutdown: async () => {},
    };

    const multi = new MultiSpanProcessor([
      failingProcessor,
      succeedingProcessor,
    ]);
    await multi.forceFlush();

    assert.strictEqual(callCount, 1);
  });

  it('should continue executing processors even if one throws in shutdown', async () => {
    let callCount = 0;
    const failingProcessor: SpanProcessor = {
      onStart: () => {},
      onEnd: () => {},
      forceFlush: async () => {},
      shutdown: async () => {
        throw new Error('Boom!');
      },
    };
    const succeedingProcessor: SpanProcessor = {
      onStart: () => {},
      onEnd: () => {},
      forceFlush: async () => {},
      shutdown: async () => {
        callCount++;
      },
    };

    const multi = new MultiSpanProcessor([
      failingProcessor,
      succeedingProcessor,
    ]);
    await multi.shutdown();

    assert.strictEqual(callCount, 1);
  });
});
