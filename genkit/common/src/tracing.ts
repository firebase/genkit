import { NodeSDK } from '@opentelemetry/sdk-node';
import {
  BatchSpanProcessor,
  SimpleSpanProcessor,
  SpanProcessor,
} from '@opentelemetry/sdk-trace-base';
import { config, getCurrentEnv } from './config.js';
import { TraceStoreExporter } from './tracing/exporter.js';
import { MultiSpanProcessor } from './tracing/multiSpanProcessor.js';

export * from './tracing/exporter.js';
export * from './tracing/firestoreTraceStore.js';
export * from './tracing/instrumentation.js';
export * from './tracing/localFileTraceStore.js';
export * from './tracing/processor.js';
export * from './tracing/types.js';

const processors: SpanProcessor[] = [];

/**
 * Enables trace spans to be written to the trace store.
 */
export async function enableTracingAndMetrics(
  traceStoreOptions: {
    processor?: 'batch' | 'simple';
  } = {}
) {
  addProcessor(
    await createTraceStoreProcessor(traceStoreOptions.processor || 'batch')
  );

  const telemetryConfig = await config.getTelemetryConfig();
  const nodeOtelConfig = telemetryConfig.getConfig() || {};

  addProcessor(nodeOtelConfig.spanProcessor as any);
  nodeOtelConfig.spanProcessor = new MultiSpanProcessor(processors) as any;
  const sdk = new NodeSDK(nodeOtelConfig);

  sdk.start();
}

/**
 * Creates a new SpanProcessor for exporting data to the configured TraceStore.
 *
 * Returns `undefined` if no trace store implementation is configured.
 */
async function createTraceStoreProcessor(
  processor: 'batch' | 'simple'
): Promise<SpanProcessor | undefined> {
  const traceStore = await config.getTraceStore();
  if (traceStore) {
    const exporter = new TraceStoreExporter(traceStore);
    return processor === 'simple' || getCurrentEnv() === 'dev'
      ? new SimpleSpanProcessor(exporter)
      : new BatchSpanProcessor(exporter);
  }
  return undefined;
}

/** Adds the given {SpanProcessor} to the list of processors */
function addProcessor(processor: SpanProcessor | undefined) {
  if (processor) processors.push(processor);
}

/**
 * Flushes all configured span processors
 */
export async function flushTracing() {
  await Promise.all(processors.map((p) => p.forceFlush()));
}
