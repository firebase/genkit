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

import { beforeAll, describe, expect, it } from '@jest/globals';
import { ReadableSpan } from '@opentelemetry/sdk-trace-base';
import { readFile } from 'fs/promises';
import { GenerateResponseData } from 'genkit';
import { TraceData } from 'genkit/tracing';
import { MediaResizer } from '../src/mediaResizer.js';

describe('MediaResizer', () => {
  var mediaResizer;

  beforeAll(() => {
    mediaResizer = new MediaResizer(128, 128);
  });

  it('resizes large images', async () => {
    const trace = JSON.parse(
      await readFile('tests/traces/chipmunkImageTrace.json', 'utf8')
    ) as TraceData;
    const spans = Object.values(trace.spans);
    const originalOutput = JSON.parse(
      spans[0].attributes['genkit:output'] as string
    ) as GenerateResponseData;
    const originalMessage =
      originalOutput.message || originalOutput.candidates?.[0]?.message!;
    const messageUrl = originalMessage.content[0].media?.url.slice(0) ?? '';

    const adjustedSpans = (await mediaResizer.resizeImages(
      spans
    )) as ReadableSpan[];
    expect(adjustedSpans).toHaveLength(1);

    const adjustedSpan = adjustedSpans[0] as ReadableSpan;
    const output = JSON.parse(
      adjustedSpan.attributes['genkit:output'] as string
    ) as GenerateResponseData;
    const message = output.message || output.candidates?.[0]?.message!;
    expect(message.content[0].media?.contentType).toBe('image/png');
    expect(message.content[0].media?.url.length).toBeLessThan(
      messageUrl.length
    );
  });
});
