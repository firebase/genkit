import * as z from 'zod';
import { FlowStateStore } from './flowTypes.js';
import { PluginProvider } from './plugin.js';
import { startReflectionApi } from './reflectionApi.js';
import { TraceStore } from './tracing/types.js';
import { Action } from './types.js';

export type AsyncProvider<T> = () => Promise<T>;

const __actionsById: Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>> = {};
const __traceStoresByEnv: Record<string, AsyncProvider<TraceStore>> = {};
const __flowStateStoresByEnv: Record<
  string,
  AsyncProvider<FlowStateStore>
> = {};
const __pluginsByName: Record<string, PluginProvider> = {};

/**
 * Type of a runnable action.
 */
export type ActionType =
  | 'chat-llm'
  | 'text-llm'
  | 'retriever'
  | 'indexer'
  | 'embedder'
  | 'evaluator'
  | 'flow'
  | 'model'
  | 'prompt';

/**
 * Looks up a registry key (action type and key) in the registry.
 */
export async function lookupAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  R extends Action<I, O>
>(key: string): Promise<R> {
  // If we don't see the key in the registry we try to initialize the plugin first.
  const pluginName = parsePluginName(key);
  if (!__actionsById[key] && pluginName) {
    await initializePlugin(pluginName);
  }
  return __actionsById[key] as R;
}

function parsePluginName(registryKey: string) {
  const tokens = registryKey.split('/');
  if (tokens.length === 4) {
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

type ActionsRecord = Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>>;

/**
 * Returns all actions in the registry.
 */
export async function listActions(): Promise<ActionsRecord> {
  for (const pluginName of Object.keys(__pluginsByName)) {
    await initializePlugin(pluginName);
  }
  return Object.assign({}, __actionsById);
}

/**
 * Registers a trace store provider for the given environment.
 */
export function registerTraceStore(
  env: string,
  traceStoreProvider: AsyncProvider<TraceStore>
) {
  __traceStoresByEnv[env] = traceStoreProvider;
}

/**
 * Looks up the trace store for the given environment.
 */
export function lookupTraceStore(env: string): Promise<TraceStore> {
  return __traceStoresByEnv[env]();
}

/**
 * Registers a flow state store provider for the given environment.
 */
export function registerFlowStateStore(
  env: string,
  flowStateStoreProvider: AsyncProvider<FlowStateStore>
) {
  __flowStateStoresByEnv[env] = flowStateStoreProvider;
}

/**
 * Looks up the flow state store for the given environment.
 */
export function lookupFlowStateStore(env: string): Promise<FlowStateStore> {
  return __flowStateStoresByEnv[env]();
}

/**
 * Registers a flow state store for the given environment.
 */
export function registerPluginProvider(name: string, provider: PluginProvider) {
  let cached;
  __pluginsByName[name] = {
    name: provider.name,
    initializer: () => {
      if (cached) {
        return cached;
      }
      cached = provider.initializer();
      return cached;
    },
  };
}

/**
 *
 */
export async function initializePlugin(name: string) {
  if (__pluginsByName[name]) {
    return await __pluginsByName[name].initializer();
  }
  return undefined;
}

/**
 * Development mode only. Starts a Reflection API so that the actions can be called by the Runner.
 */
if (process.env.GENKIT_ENV === 'dev') {
  startReflectionApi();
}

export function __hardResetRegistryForTesting() {
  deleteAll(__actionsById);
  deleteAll(__traceStoresByEnv);
  deleteAll(__flowStateStoresByEnv);
  deleteAll(__pluginsByName);
}

function deleteAll(map: Record<any, any>) {
  Object.keys(map).forEach((key) => delete map[key]);
}
