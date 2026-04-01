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

import { Context } from '@opentelemetry/api';
import { MetricReader } from '@opentelemetry/sdk-metrics';
import { NodeSDK } from '@opentelemetry/sdk-node';
import {
  BatchSpanProcessor,
  SimpleSpanProcessor,
  type ReadableSpan,
  type Span,
  type SpanProcessor,
} from '@opentelemetry/sdk-trace-base';
import { logger } from '../logging.js';
import type { TelemetryConfig } from '../telemetryTypes.js';
import { setTelemetryProvider } from '../tracing.js';
import { isDevEnv } from '../utils.js';
import { TraceServerExporter, setTelemetryServerUrl } from './exporter.js';
import { RealtimeSpanProcessor } from './realtime-span-processor.js';

let telemetrySDK: NodeSDK | null = null;
let nodeOtelConfig: TelemetryConfig | null = null;
let isSigtermHandlerRegistered = false;

export function initNodeTelemetryProvider() {
  setTelemetryProvider({
    enableTelemetry,
    flushTracing,
  });
}

/**
 * MultiSpanProcessor is a multiplexer that allows Genkit to register multiple
 * span processors reliably.
 *
 * We provide it as the sole entry in the `spanProcessors` array to the
 * OpenTelemetry NodeSDK because the SDK's internal logic for merging
 * `traceExporter`, `spanProcessor` (singular), and `spanProcessors` (plural)
 * varies across versions and can lead to exporters being silently overwritten
 * or ignored.
 *
 * By wrapping all processors into this single delegate, we guarantee that
 * Genkit's internal telemetry and any user-provided exporters both receive
 * every start and end event.
 */
export class MultiSpanProcessor implements SpanProcessor {
  constructor(private processors: SpanProcessor[]) {}
  onStart(span: Span, parentContext: Context) {
    this.processors.forEach((p) => {
      try {
        p.onStart(span, parentContext);
      } catch (e) {
        logger.defaultLogger.error(
          `Error in span processor (${p.constructor.name}) onStart: ${e}`
        );
      }
    });
  }
  onEnd(span: ReadableSpan) {
    this.processors.forEach((p) => {
      try {
        p.onEnd(span);
      } catch (e) {
        logger.defaultLogger.error(
          `Error in span processor (${p.constructor.name}) onEnd: ${e}`
        );
      }
    });
  }
  async forceFlush() {
    await Promise.all(
      this.processors.map(async (p) => {
        try {
          await p.forceFlush();
        } catch (e) {
          logger.defaultLogger.error(
            `Error in span processor (${p.constructor.name}) forceFlush: ${e}`
          );
        }
      })
    );
  }
  async shutdown() {
    await Promise.all(
      this.processors.map(async (p) => {
        try {
          await p.shutdown();
        } catch (e) {
          logger.defaultLogger.error(
            `Error in span processor (${p.constructor.name}) shutdown: ${e}`
          );
        }
      })
    );
  }
}

/**
 * Enables tracing and metrics open telemetry configuration.
 */
async function enableTelemetry(
  telemetryConfig: TelemetryConfig | Promise<TelemetryConfig>
) {
  if (process.env.GENKIT_TELEMETRY_SERVER) {
    setTelemetryServerUrl(process.env.GENKIT_TELEMETRY_SERVER);
  }

  telemetryConfig =
    telemetryConfig instanceof Promise
      ? await telemetryConfig
      : telemetryConfig;

  if (telemetrySDK) {
    await cleanUpTracing();
  }

  nodeOtelConfig = { ...telemetryConfig };

  const processors: SpanProcessor[] = [createTelemetryServerProcessor()];
  if (nodeOtelConfig.spanProcessors) {
    processors.push(...nodeOtelConfig.spanProcessors);
  }
  if (nodeOtelConfig.spanProcessor) {
    processors.push(nodeOtelConfig.spanProcessor);
  }
  if (nodeOtelConfig.traceExporter) {
    processors.push(new BatchSpanProcessor(nodeOtelConfig.traceExporter));
  }

  if (processors.length > 1) {
    nodeOtelConfig.spanProcessors = [new MultiSpanProcessor(processors)];
  } else {
    nodeOtelConfig.spanProcessors = processors;
  }
  delete nodeOtelConfig.spanProcessor;
  delete nodeOtelConfig.traceExporter;

  telemetrySDK = new NodeSDK(nodeOtelConfig);
  telemetrySDK.start();

  if (!isSigtermHandlerRegistered) {
    let isShuttingDown = false;
    const shutdownHandler = (signal: string) => () => {
      if (isShuttingDown) return; // Prevent SIGTERM + SIGINT race
      isShuttingDown = true;
      cleanUpTracing().finally(() => {
        process.kill(process.pid, signal);
      });
    };
    process.once('SIGTERM', shutdownHandler('SIGTERM'));
    process.once('SIGINT', shutdownHandler('SIGINT'));
    isSigtermHandlerRegistered = true;
  }
}

async function cleanUpTracing(): Promise<void> {
  if (!telemetrySDK) {
    return;
  }

  // Metrics are not flushed as part of the shutdown operation. If metrics
  // are enabled, we need to manually flush them *before* the reader
  // receives shutdown order.
  try {
    await maybeFlushMetrics();
  } catch (e) {
    logger.defaultLogger.error(`Error flushing metrics during shutdown: ${e}`);
  }

  try {
    await telemetrySDK.shutdown();
    logger.debug('OpenTelemetry SDK shut down.');
  } catch (e) {
    logger.defaultLogger.error(`Error shutting down OpenTelemetry SDK: ${e}`);
  } finally {
    telemetrySDK = null;
  }
}

/**
 * Creates a new SpanProcessor for exporting data to the telemetry server.
 */
function createTelemetryServerProcessor(): SpanProcessor {
  const exporter = new TraceServerExporter();
  // Use RealtimeSpanProcessor in dev environment (unless disabled), or when explicitly enabled
  const enableRealTimeTelemetry =
    process.env.GENKIT_ENABLE_REALTIME_TELEMETRY === 'true';
  if (isDevEnv() && enableRealTimeTelemetry) {
    return new RealtimeSpanProcessor(exporter);
  } else if (isDevEnv()) {
    return new SimpleSpanProcessor(exporter);
  }
  return new BatchSpanProcessor(exporter);
}

/** Flush metrics if present. */
async function maybeFlushMetrics(): Promise<void> {
  const readers: MetricReader[] = [];
  if (nodeOtelConfig?.metricReader) {
    readers.push(nodeOtelConfig.metricReader as MetricReader);
  }
  if (nodeOtelConfig?.metricReaders) {
    readers.push(...(nodeOtelConfig.metricReaders as MetricReader[]));
  }
  await Promise.all(
    readers.map(async (r) => {
      try {
        await r.forceFlush();
      } catch (e) {
        logger.defaultLogger.error(`Error flushing metrics: ${e}`);
      }
    })
  );
}

/**
 * Flushes all configured span processors.
 */
async function flushTracing() {
  if (nodeOtelConfig?.spanProcessors) {
    await Promise.all(nodeOtelConfig.spanProcessors.map((p) => p.forceFlush()));
  }
}
