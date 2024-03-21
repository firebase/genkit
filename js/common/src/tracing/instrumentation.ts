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

import {
  Link,
  Span as ApiSpan,
  SpanStatusCode,
  trace,
} from '@opentelemetry/api';
import { AsyncLocalStorage } from 'node:async_hooks';
import { SpanMetadata } from './types';

export const spanMetadataAls = new AsyncLocalStorage<SpanMetadata>();

export const ATTR_PREFIX = 'genkit';
export const SPAN_TYPE_ATTR = ATTR_PREFIX + ':type';
const TRACER_NAME = 'genkit-tracer';
const TRACER_VERSION = 'v1';

/**
 *
 */
export async function newTrace<T>(
  opts: {
    name: string;
    labels?: Record<string, string>;
    links?: Link[];
  },
  fn: (metadata: SpanMetadata, rootSpan: ApiSpan) => Promise<T>
) {
  return await runInNewSpan(
    {
      metadata: {
        name: opts.name,
        isRoot: true,
      },
      labels: opts.labels,
      links: opts.links,
    },
    async (metadata, otSpan) => {
      return await fn(metadata, otSpan);
    }
  );
}

/**
 *
 */
export async function runInNewSpan<T>(
  opts: {
    metadata: SpanMetadata;
    labels?: Record<string, string>;
    links?: Link[];
  },
  fn: (metadata: SpanMetadata, otSpan: ApiSpan, isRoot: boolean) => Promise<T>
): Promise<T> {
  const tracer = trace.getTracer(TRACER_NAME, TRACER_VERSION);
  const parentStep = spanMetadataAls.getStore();
  const isInRoot = parentStep?.isRoot === true;
  return await tracer.startActiveSpan(
    opts.metadata.name,
    { links: opts.links },
    async (otSpan) => {
      if (opts.labels) otSpan.setAttributes(opts.labels);
      try {
        const parentPath = parentStep?.path || '';
        opts.metadata.path = parentPath + '/' + opts.metadata.name;
        const output = await spanMetadataAls.run(opts.metadata, () =>
          fn(opts.metadata, otSpan, isInRoot)
        );
        if (opts.metadata.state !== 'error') {
          opts.metadata.state = 'success';
        }
        return output;
      } catch (e) {
        opts.metadata.state = 'error';
        otSpan.setStatus({
          code: SpanStatusCode.ERROR,
          message: JSON.stringify(e),
        });
        throw e;
      } finally {
        otSpan.setAttributes(metadataToAttributes(opts.metadata));
        otSpan.end();
      }
    }
  );
}

function metadataToAttributes(metadata: SpanMetadata): Record<string, string> {
  const out = {} as Record<string, string>;
  Object.keys(metadata).forEach((key) => {
    if (
      key === 'metadata' &&
      typeof metadata[key] === 'object' &&
      metadata.metadata
    ) {
      Object.entries(metadata.metadata).forEach(([metaKey, value]) => {
        out[ATTR_PREFIX + ':metadata:' + metaKey] = value;
      });
    } else if (key === 'input' || typeof metadata[key] === 'object') {
      out[ATTR_PREFIX + ':' + key] = JSON.stringify(metadata[key]);
    } else {
      out[ATTR_PREFIX + ':' + key] = metadata[key];
    }
  });
  return out;
}

/**
 * Sets provided attribute value in the current span.
 */
export function setCustomMetadataAttribute(key: string, value: string) {
  const currentStep = getCurrentSpan();
  if (!currentStep) {
    return;
  }
  if (!currentStep.metadata) {
    currentStep.metadata = {};
  }
  currentStep.metadata[key] = value;
}

/**
 * Sets provided attribute values in the current span.
 */
export function setCustomMetadataAttributes(values: Record<string, string>) {
  const currentStep = getCurrentSpan();
  if (!currentStep) {
    return;
  }
  if (!currentStep.metadata) {
    currentStep.metadata = {};
  }
  for (const [key, value] of Object.entries(values)) {
    currentStep.metadata[key] = value;
  }
}

function getCurrentSpan(): SpanMetadata {
  const step = spanMetadataAls.getStore();
  if (!step) {
    throw new Error('running outside step context');
  }
  return step;
}
