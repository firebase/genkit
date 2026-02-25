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

import { context, trace } from '@opentelemetry/api';
import { AsyncLocalStorageContextManager } from '@opentelemetry/context-async-hooks';
import {
  BasicTracerProvider,
  BatchSpanProcessor,
  SimpleSpanProcessor,
  type SpanProcessor,
} from '@opentelemetry/sdk-trace-base';
import type { TelemetryConfig } from '../telemetryTypes.js';
import type { TelemetryProvider } from '../tracing.js';
import { TraceServerExporter, setTelemetryServerUrl } from './exporter.js';

/**
 * Options for the fetch-compatible telemetry provider.
 * Uses only fetch and standard APIs (no Node.js SDK), suitable for workers.
 */
export interface FetchTelemetryProviderOptions {
  /**
   * URL of the Genkit telemetry server (e.g. from dev UI or your own collector).
   * If not set, GENKIT_TELEMETRY_SERVER env var is used when enableTelemetry runs.
   */
  serverUrl?: string;
  /**
   * If true, use SimpleSpanProcessor for more real-time export (e.g. in dev).
   * Default: true. Set to false for BatchSpanProcessor (production).
   */
  realtime?: boolean;
}

/**
 * Telemetry provider that uses only fetch-compatible APIs.
 * Use this in worker environments (Cloudflare Workers, Vercel Edge, etc.) where
 * the Node.js OpenTelemetry SDK is not available.
 *
 * When the runtime has AsyncLocalStorage (e.g. Cloudflare Workers with `nodejs_compat`),
 * OTel context propagation is enabled so parent-child span links are preserved across
 * async boundaries and traces are fully hierarchical.
 *
 * Set via runtime config before any other genkit imports:
 *
 * @example
 * ```ts
 * import { setGenkitRuntimeConfig } from 'genkit';
 * import { FetchTelemetryProvider } from 'genkit/tracing';
 *
 * setGenkitRuntimeConfig({
 *   jsonSchemaMode: 'interpret',
 *   sandboxedRuntime: true,
 *   telemetry: new FetchTelemetryProvider({
 *     serverUrl: 'https://your-telemetry-server.example.com',
 *   }),
 * });
 *
 * // Then import flows/actions
 * import { flow, run } from 'genkit';
 * ```
 */
export class FetchTelemetryProvider implements TelemetryProvider {
  private readonly options: FetchTelemetryProviderOptions;
  private spanProcessors: SpanProcessor[] = [];

  constructor(options: FetchTelemetryProviderOptions = {}) {
    this.options = options;
  }

  async enableTelemetry(
    telemetryConfig: TelemetryConfig | Promise<TelemetryConfig>
  ): Promise<void> {
    const config =
      telemetryConfig instanceof Promise
        ? await telemetryConfig
        : telemetryConfig;
    const serverUrl =
      this.options.serverUrl ??
      (typeof process !== 'undefined' && process.env?.GENKIT_TELEMETRY_SERVER);
    if (typeof serverUrl === 'string') {
      setTelemetryServerUrl(serverUrl);
    }

    const exporter = new TraceServerExporter();
    const processor: SpanProcessor =
      this.options.realtime !== false
        ? new SimpleSpanProcessor(exporter)
        : new BatchSpanProcessor(exporter);

    this.spanProcessors = [processor];

    if (config?.spanProcessors?.length) {
      this.spanProcessors.push(...config.spanProcessors);
    }

    // When AsyncLocalStorage is available (e.g. Node, Cloudflare Workers with nodejs_compat),
    // enable OTel context propagation so parent-child span links work across await.
    try {
      const contextManager = new AsyncLocalStorageContextManager();
      contextManager.enable();
      context.setGlobalContextManager(contextManager);
    } catch {
      // No async_hooks / AsyncLocalStorage (e.g. some edge runtimes); spans still work, hierarchy may be flat.
    }

    const provider = new BasicTracerProvider();
    for (const p of this.spanProcessors) {
      provider.addSpanProcessor(p);
    }
    trace.setGlobalTracerProvider(provider);
  }

  async flushTracing(): Promise<void> {
    await Promise.all(this.spanProcessors.map((p) => p.forceFlush()));
  }
}
