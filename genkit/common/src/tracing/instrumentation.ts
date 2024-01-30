import { AsyncLocalStorage } from "node:async_hooks";
import { SpanStatusCode, trace, Span as ApiSpan, Link } from "@opentelemetry/api";
import { SpanMetadata } from "./types";

const stepAsyncLocalStorage = new AsyncLocalStorage<SpanMetadata>();

export const ATTR_PREFIX = "genkit";
export const SPAN_TYPE_ATTR = ATTR_PREFIX + ":type";
const TRACER_NAME = "genkit-tracer";
const TRACER_VERSION = "v1";

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
  const parentStep = stepAsyncLocalStorage.getStore();
  const isInRoot = parentStep?.isRoot === true;
  return await tracer.startActiveSpan(opts.metadata.name, { links: opts.links }, async (otSpan) => {
    if (opts.labels) otSpan.setAttributes(opts.labels);
    try {
      const output = await stepAsyncLocalStorage.run(opts.metadata, () =>
        fn(opts.metadata, otSpan, isInRoot)
      );
      opts.metadata.output = JSON.stringify(output);
      return output;
    } catch (e) {
      opts.metadata.state = "error";
      otSpan.setStatus({
        code: SpanStatusCode.ERROR,
        message: JSON.stringify(e),
      });
      throw e;
    } finally {
      otSpan.setAttributes(metadataToAttributes(opts.metadata));
      otSpan.end();
    }
  });
}

function metadataToAttributes(metadata: SpanMetadata): Record<string, string> {
  const out = {} as Record<string, string>;
  Object.keys(metadata).forEach((key) => {
    if (key === "metadata" && typeof metadata[key] === "object" && metadata.metadata) {
      Object.entries(metadata.metadata).forEach(([metaKey, value]) => {
        out[ATTR_PREFIX + ":metadata:" + metaKey] = value;
      });
    } else if (key === "input" || typeof metadata[key] === "object") {
      out[ATTR_PREFIX + ":" + key] = JSON.stringify(metadata[key]);
    } else {
      out[ATTR_PREFIX + ":" + key] = metadata[key];
    }
  });
  return out;
}

/**
 *
 */
export function setCustomMetadataAttribute(key: string, value: any) {
  const currentStep = getCurrentSpan();
  if (!currentStep) {
    return;
  }
  if (!currentStep.metadata) {
    currentStep.metadata = {};
  }
  currentStep.metadata[key] = value;
}

function getCurrentSpan(): SpanMetadata {
  const step = stepAsyncLocalStorage.getStore();
  if (!step) {
    throw new Error("running outside step context");
  }
  return step;
}
