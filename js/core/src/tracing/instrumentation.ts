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
  Span as ApiSpan,
  Link,
  ROOT_CONTEXT,
  SpanStatusCode,
  trace,
} from '@opentelemetry/api';
import { performance } from 'node:perf_hooks';
import { HasRegistry, Registry } from '../registry.js';
import { ensureBasicTelemetryInstrumentation } from '../tracing.js';
import { PathMetadata, SpanMetadata, TraceMetadata } from './types.js';

export const spanMetadataAlsKey = 'core.tracing.instrumentation.span';
export const traceMetadataAlsKey = 'core.tracing.instrumentation.trace';

export const ATTR_PREFIX = 'genkit';
/** @hidden */
export const SPAN_TYPE_ATTR = ATTR_PREFIX + ':type';
const TRACER_NAME = 'genkit-tracer';
const TRACER_VERSION = 'v1';

/**
 * @hidden
 */
export async function newTrace<T>(
  registry: Registry | HasRegistry,
  opts: {
    name: string;
    labels?: Record<string, string>;
    links?: Link[];
  },
  fn: (metadata: SpanMetadata, rootSpan: ApiSpan) => Promise<T>
) {
  registry = (registry as HasRegistry).registry
    ? (registry as HasRegistry).registry
    : (registry as Registry);

  await ensureBasicTelemetryInstrumentation();
  const traceMetadata: TraceMetadata = registry.asyncStore.getStore(
    traceMetadataAlsKey
  ) || {
    paths: new Set<PathMetadata>(),
    timestamp: performance.now(),
    featureName: opts.name,
  };
  return await registry.asyncStore.run(traceMetadataAlsKey, traceMetadata, () =>
    runInNewSpan(
      registry,
      {
        metadata: {
          name: opts.name,
        },
        labels: opts.labels,
        links: opts.links,
      },
      async (metadata, otSpan) => {
        return await fn(metadata, otSpan);
      }
    )
  );
}

/**
 * Runs the provided function in a new span.
 *
 * @hidden
 */
export async function runInNewSpan<T>(
  registry: Registry | HasRegistry,
  opts: {
    metadata: SpanMetadata;
    labels?: Record<string, string>;
    links?: Link[];
  },
  fn: (metadata: SpanMetadata, otSpan: ApiSpan, isRoot: boolean) => Promise<T>
): Promise<T> {
  await ensureBasicTelemetryInstrumentation();
  const resolvedRegistry = (registry as HasRegistry).registry
    ? (registry as HasRegistry).registry
    : (registry as Registry);

  const tracer = trace.getTracer(TRACER_NAME, TRACER_VERSION);
  const parentStep =
    resolvedRegistry.asyncStore.getStore<SpanMetadata>(spanMetadataAlsKey);
  const isInRoot = parentStep?.isRoot === true;
  if (!parentStep) opts.metadata.isRoot ||= true;
  return await tracer.startActiveSpan(
    opts.metadata.name,
    { links: opts.links, root: opts.metadata.isRoot },
    async (otSpan) => {
      if (opts.labels) otSpan.setAttributes(opts.labels);
      try {
        opts.metadata.path = buildPath(
          opts.metadata.name,
          parentStep?.path || '',
          opts.labels
        );

        const output = await resolvedRegistry.asyncStore.run(
          spanMetadataAlsKey,
          opts.metadata,
          () => fn(opts.metadata, otSpan, isInRoot)
        );
        if (opts.metadata.state !== 'error') {
          opts.metadata.state = 'success';
        }

        recordPath(resolvedRegistry, opts.metadata);
        return output;
      } catch (e) {
        recordPath(resolvedRegistry, opts.metadata, e);
        opts.metadata.state = 'error';
        otSpan.setStatus({
          code: SpanStatusCode.ERROR,
          message: getErrorMessage(e),
        });
        if (e instanceof Error) {
          otSpan.recordException(e);
        }
        throw e;
      } finally {
        otSpan.setAttributes(metadataToAttributes(opts.metadata));
        otSpan.end();
      }
    }
  );
}

/**
 * Creates a new child span and attaches it to a previously created trace. This
 * is useful, for example, for adding deferred user engagement metadata.
 *
 * @hidden
 */
export async function appendSpan(
  traceId: string,
  parentSpanId: string,
  metadata: SpanMetadata,
  labels?: Record<string, string>
) {
  await ensureBasicTelemetryInstrumentation();

  const tracer = trace.getTracer(TRACER_NAME, TRACER_VERSION);

  const spanContext = trace.setSpanContext(ROOT_CONTEXT, {
    traceId: traceId,
    traceFlags: 1, // sampled
    spanId: parentSpanId,
  });

  // TODO(abrook): add explicit start time to align with parent
  const span = tracer.startSpan(metadata.name, {}, spanContext);
  span.setAttributes(metadataToAttributes(metadata));
  if (labels) {
    span.setAttributes(labels);
  }
  span.end();
}

function getErrorMessage(e: any): string {
  if (e instanceof Error) {
    return e.message;
  }
  return `${e}`;
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
 *
 * @hidden
 */
export function setCustomMetadataAttribute(
  registry: Registry,
  key: string,
  value: string
) {
  const currentStep = getCurrentSpan(registry);
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
 *
 * @hidden
 */
export function setCustomMetadataAttributes(
  registry: Registry,
  values: Record<string, string>
) {
  const currentStep = getCurrentSpan(registry);
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

/**
 * Converts a fully annotated path to a friendly display version for logs
 *
 * @hidden
 */
export function toDisplayPath(path: string): string {
  const pathPartRegex = /\{([^\,}]+),[^\}]+\}/g;
  return Array.from(path.matchAll(pathPartRegex), (m) => m[1]).join(' > ');
}

function getCurrentSpan(registry: Registry): SpanMetadata {
  const step = registry.asyncStore.getStore<SpanMetadata>(spanMetadataAlsKey);
  if (!step) {
    throw new Error('running outside step context');
  }
  return step;
}

function buildPath(
  name: string,
  parentPath: string,
  labels?: Record<string, string>
) {
  const stepType =
    labels && labels['genkit:type']
      ? `,t:${labels['genkit:metadata:subtype'] === 'flow' ? 'flow' : labels['genkit:type']}`
      : '';
  return parentPath + `/{${name}${stepType}}`;
}

function recordPath(registry: Registry, spanMeta: SpanMetadata, err?: any) {
  const path = spanMeta.path || '';
  const decoratedPath = decoratePathWithSubtype(spanMeta);
  // Only add the path if a child has not already been added. In the event that
  // an error is rethrown, we don't want to add each step in the unwind.
  const paths = Array.from(
    registry.asyncStore.getStore<TraceMetadata>(traceMetadataAlsKey)?.paths ||
      new Set<PathMetadata>()
  );
  const status = err ? 'failure' : 'success';
  if (!paths.some((p) => p.path.startsWith(path) && p.status === status)) {
    const now = performance.now();
    const start =
      registry.asyncStore.getStore<TraceMetadata>(traceMetadataAlsKey)
        ?.timestamp || now;
    registry.asyncStore
      .getStore<TraceMetadata>(traceMetadataAlsKey)
      ?.paths?.add({
        path: decoratedPath,
        error: err?.name,
        latency: now - start,
        status,
      });
  }
  spanMeta.path = decoratedPath;
}

function decoratePathWithSubtype(metadata: SpanMetadata): string {
  if (!metadata.path) {
    return '';
  }

  const pathComponents = metadata.path.split('}/{');

  if (pathComponents.length == 1) {
    return metadata.path;
  }

  const stepSubtype =
    metadata.metadata && metadata.metadata['subtype']
      ? `,s:${metadata.metadata['subtype']}`
      : '';
  const root = `${pathComponents.slice(0, -1).join('}/{')}}/`;
  const decoratedStep = `{${pathComponents.at(-1)?.slice(0, -1)}${stepSubtype}}`;
  return root + decoratedStep;
}
