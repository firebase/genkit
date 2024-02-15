import { FlowStateStore } from './flowTypes';
import { TraceStore } from './tracing';
import { Action } from './types';
import { z } from 'zod';

export interface Provider<T> {
  id: string;
  value: T;
}

export interface PluginProvider<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny
> {
  name: string;
  initializer: () => Plugin<I, O>;
}

export interface Plugin<I extends z.ZodTypeAny, O extends z.ZodTypeAny> {
  models?: Action<I, O>[];
  retrievers?: Action<I, O>[];
  embedders?: Action<I, O>[];
  indexers?: Action<I, O>[];
  flowStateStore?: Provider<FlowStateStore>;
  traceStore?: Provider<TraceStore>;
}

/**
 *
 */
export function genkitPlugin<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  Config
>(
  pluginName: string,
  initFn: (config?: Config) => Plugin<I, O>
): (c?: Config) => PluginProvider<I, O> {
  return (config?) => ({
    name: pluginName,
    initializer: () => initFn(config),
  });
}
