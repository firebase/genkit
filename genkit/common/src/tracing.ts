import { MetricExporter } from "@google-cloud/opentelemetry-cloud-monitoring-exporter";
import { GcpDetectorSync } from "@google-cloud/opentelemetry-resource-util";
import { AsyncLocalStorageContextManager } from "@opentelemetry/context-async-hooks";
import { Resource } from "@opentelemetry/resources";
import { PeriodicExportingMetricReader } from "@opentelemetry/sdk-metrics";
import { NodeSDK } from "@opentelemetry/sdk-node";
import {
  BatchSpanProcessor,
  SimpleSpanProcessor,
  SpanProcessor,
} from "@opentelemetry/sdk-trace-base";
import { meterProvider } from "./metrics";
import * as registry from "./registry";
import { getProjectId } from "./runtime";
import { TraceStoreExporter } from "./tracing/exporter";
import { config } from "./config";
import { TraceStore } from "./tracing";

export * from "./tracing/exporter";
export * from "./tracing/firestoreTraceStore";
export * from "./tracing/localFileStore";
export * from "./tracing/instrumentation";
export * from "./tracing/processor";
export * from "./tracing/types";

const processors: SpanProcessor[] = [];

/**
 *
 */
export function enableTracingAndMetrics(
  options: { projId?: string; processor: "batch" | "simple" } = {
    processor: "batch",
  }
) {
  if (!options.projId) {
    options.projId = getProjectId();
  }

  const contextManager = new AsyncLocalStorageContextManager(); // this contextManager is not required if we do not want to invoke sdk#configureTracerProvider - can be removed
  contextManager.enable();

  const traceStore = lookupTraceStore();
  const exporter = new TraceStoreExporter(traceStore);
  const spanProcessor =
    options.processor === "batch"
      ? new BatchSpanProcessor(exporter)
      : new SimpleSpanProcessor(exporter);

  processors.push(spanProcessor);

  const metricReader = new PeriodicExportingMetricReader({
    // Export metrics every 10 seconds. 5 seconds is the smallest sample period allowed by
    // Cloud Monitoring.
    exportIntervalMillis: 10_000,
    exporter: new MetricExporter(),
  }) as any;
  meterProvider.addMetricReader(metricReader);

  const resource = new Resource({
    type: "global",
  }).merge(new GcpDetectorSync().detect());

  const sdk = new NodeSDK({
    resource,
    // TODO: fix this hack (any), SpanProcessor type does not resolve, suspect workspace deps issue
    spanProcessor: spanProcessor as any, 
    contextManager,
  });
  sdk.start();
}

/**
 *
 */
export async function flushTracing() {
  await Promise.all(processors.map((p) => p.forceFlush()));
}

// TODO: temporary, the trace store registration and lookup needs rework.
let tracestoreCache: TraceStore;
export function lookupTraceStore(): TraceStore {
  if (tracestoreCache) {
    return tracestoreCache;
  }
  const legacyStore = registry.lookup("/flows/traceStore");
  if (legacyStore) {
    tracestoreCache = legacyStore;
    return legacyStore;
  }
  const pluginName = registry.lookup("/trace/storePlugin")
  const plugin = config.plugins?.find(p => p.name === pluginName);
  if (!plugin) {
    throw new Error("Unable to resolve plugin name: " + pluginName);
  }
  const provider = plugin.provides.traceStore;
  if (!provider) {
    throw new Error("Unable to resolve provider `traceStore` for plugin: " + pluginName);
  }
  const tracestore = registry.lookup(`/traceStore/${provider.id}`)
  if (!tracestore) {
    throw new Error("Unable to resolve tracestore for plugin: " + pluginName);
  }
  tracestoreCache = tracestore;
  return tracestore as TraceStore;
}