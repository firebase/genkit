import * as z from 'zod';
import { FlowStateStore } from './flowTypes';
import { PluginProvider } from './plugin';
import { startReflectionApi } from './reflectionApi';
import { TraceStore } from './tracing/types';
import { Action } from './types';

type Provider<T> = () => T;

const __actionsById: Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>> = {};
const __traceStoresByEnv: Record<string, Provider<TraceStore>> = {};
const __flowStateStoresByEnv: Record<string, Provider<FlowStateStore>> = {};
const __pluginsByName: Record<string, PluginProvider<any, any, any>> = {};

/**
 * Type of a runnable action.
 */
export type ActionType =
  | 'chat-llm'
  | 'text-llm'
  | 'retriever'
  | 'indexer'
  | 'embedder'
  | 'flow'
  | 'model';

/**
 * Looks up a registry key (action type and key) in the registry.
 */
export function lookupAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  R extends Action<I, O>
>(key: string): R {
  // If we don't see the key in the registry we try to initialize the plugin first.
  const pluginName = parsePluginName(key);
  if (!__actionsById[key] && pluginName) {
    initializePlugin(pluginName);
  }
  return __actionsById[key] as R;
}

function parsePluginName(registryKey: string) {
  const tokens = registryKey.split("/");
  if (tokens.length == 4) {
    return tokens[2];
  }
  return undefined;
}

/**
 * Registers an action in the registry.
 */
export function registerAction<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  type: ActionType,
  id: string,
  action: Action<I, O>
) {
  const key = `/${type}/${id}`;
  if (__actionsById.hasOwnProperty(key)) {
    console.log(`WARNING: ${key} already has an entry in the registry.`);
  }
  __actionsById[key] = action;
}

/**
 * Returns all actions in the registry.
 */
export function listActions(): Record<
  string,
  Action<z.ZodTypeAny, z.ZodTypeAny>
> {
  Object.keys(__pluginsByName).forEach((pluginName) => {
    initializePlugin(pluginName)
  })
  return Object.assign({}, __actionsById);
}

/**
 * Registers a trace store provider for the given environment.
 */
export function registerTraceStore(env: string, traceStoreProvider: Provider<TraceStore>) {
  __traceStoresByEnv[env] = traceStoreProvider;
}

/**
 * Looks up the trace store for the given environment.
 */
export function lookupTraceStore(env: string): TraceStore {
  return __traceStoresByEnv[env]();
}

/**
 * Registers a flow state store provider for the given environment.
 */
export function registerFlowStateStore(
  env: string,
  flowStateStoreProvider: Provider<FlowStateStore>
) {
  __flowStateStoresByEnv[env] = flowStateStoreProvider;
}

/**
 * Looks up the flow state store for the given environment.
 */
export function lookupFlowStateStore(env: string): FlowStateStore {
  return __flowStateStoresByEnv[env]();
}


/**
 * Registers a flow state store for the given environment.
 */
export function registerPluginProvider(
  name: string,
  provider: PluginProvider<any, any, any>
) {
  var cached;
  __pluginsByName[name] = {
    name: provider.name,
    initializer: () => {
      if (cached) {
        return cached;
      }
      cached = provider.initializer();
      return cached;
    }
  };
}

export function initializePlugin(name: string) {
  if (__pluginsByName[name]) {
    return __pluginsByName[name].initializer();
  }
  return undefined;
}


/**
 * Development mode only. Starts a Reflection API so that the actions can be called by the Runner.
 */
if (process.env.GENKIT_ENV === 'dev') {
  startReflectionApi();
}
