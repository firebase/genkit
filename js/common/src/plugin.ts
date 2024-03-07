import { FlowStateStore } from './flowTypes.js';
import { TraceStore } from './tracing.js';
import { Action } from './types.js';
import { TelemetryConfig } from './telemetryTypes.js';
import { z } from 'zod';

export interface Provider<T> {
  id: string;
  value: T;
}

export interface PluginProvider {
  name: string;
  initializer: () => Promise<InitializedPlugin>;
}

export interface InitializedPlugin {
  models?: Action<z.ZodTypeAny, z.ZodTypeAny>[];
  retrievers?: Action<z.ZodTypeAny, z.ZodTypeAny>[];
  embedders?: Action<z.ZodTypeAny, z.ZodTypeAny>[];
  indexers?: Action<z.ZodTypeAny, z.ZodTypeAny>[];
  evaluators?: Action<z.ZodTypeAny, z.ZodTypeAny>[];
  flowStateStore?: Provider<FlowStateStore>;
  traceStore?: Provider<TraceStore>;
  telemetry?: Provider<TelemetryConfig>;
}

type PluginInit = (...args: any[]) => Promise<InitializedPlugin>;

export type Plugin<T extends any[]> = (...args: T) => PluginProvider;

/**
 *
 */
export function genkitPlugin<T extends PluginInit>(
  pluginName: string,
  initFn: T
): Plugin<Parameters<T>> {
  return (...args: Parameters<T>) => ({
    name: pluginName,
    initializer: () => initFn(...args),
  });
}
