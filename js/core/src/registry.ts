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

import * as z from 'zod';
import { Action } from './action.js';
import { FlowStateStore } from './flowTypes.js';
import { logger } from './logging.js';
import { PluginProvider } from './plugin.js';
import { startReflectionApi } from './reflectionApi.js';
import { JSONSchema } from './schema.js';
import { TraceStore } from './tracing/types.js';

export type AsyncProvider<T> = () => Promise<T>;

const ACTIONS_BY_ID = 'genkit__ACTIONS_BY_ID';
const TRACE_STORES_BY_ENV = 'genkit__TRACE_STORES_BY_ENV';
const FLOW_STATE_STORES_BY_ENV = 'genkit__FLOW_STATE_STORES_BY_ENV';
const PLUGINS_BY_NAME = 'genkit__PLUGINS_BY_NAME';
const SCHEMAS_BY_NAME = 'genkit__SCHEMAS_BY_NAME';

function actionsById(): Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>> {
  if (global[ACTIONS_BY_ID] === undefined) {
    global[ACTIONS_BY_ID] = {};
  }
  return global[ACTIONS_BY_ID];
}
function traceStoresByEnv(): Record<string, AsyncProvider<TraceStore>> {
  if (global[TRACE_STORES_BY_ENV] === undefined) {
    global[TRACE_STORES_BY_ENV] = {};
  }
  return global[TRACE_STORES_BY_ENV];
}
function flowStateStoresByEnv(): Record<string, AsyncProvider<FlowStateStore>> {
  if (global[FLOW_STATE_STORES_BY_ENV] === undefined) {
    global[FLOW_STATE_STORES_BY_ENV] = {};
  }
  return global[FLOW_STATE_STORES_BY_ENV];
}
function pluginsByName(): Record<string, PluginProvider> {
  if (global[PLUGINS_BY_NAME] === undefined) {
    global[PLUGINS_BY_NAME] = {};
  }
  return global[PLUGINS_BY_NAME];
}
function schemasByName(): Record<
  string,
  { schema?: z.ZodTypeAny; jsonSchema?: JSONSchema }
> {
  if (global[SCHEMAS_BY_NAME] === undefined) {
    global[SCHEMAS_BY_NAME] = {};
  }
  return global[SCHEMAS_BY_NAME];
}

/**
 * Type of a runnable action.
 */
export type ActionType =
  | 'custom'
  | 'retriever'
  | 'indexer'
  | 'embedder'
  | 'evaluator'
  | 'flow'
  | 'model'
  | 'prompt'
  | 'tool';

/**
 * Looks up a registry key (action type and key) in the registry.
 */
export async function lookupAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  R extends Action<I, O>,
>(key: string): Promise<R> {
  // If we don't see the key in the registry we try to initialize the plugin first.
  const pluginName = parsePluginName(key);
  if (!actionsById()[key] && pluginName) {
    await initializePlugin(pluginName);
  }
  return actionsById()[key] as R;
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
  action: Action<I, O>
) {
  logger.info(`Registering ${type}: ${action.__action.name}`);
  const key = `/${type}/${action.__action.name}`;
  if (actionsById().hasOwnProperty(key)) {
    logger.warn(
      `WARNING: ${key} already has an entry in the registry. Overwriting.`
    );
  }
  actionsById()[key] = action;
}

type ActionsRecord = Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>>;

/**
 * Returns all actions in the registry.
 */
export async function listActions(): Promise<ActionsRecord> {
  for (const pluginName of Object.keys(pluginsByName())) {
    await initializePlugin(pluginName);
  }
  return Object.assign({}, actionsById());
}

/**
 * Registers a trace store provider for the given environment.
 */
export function registerTraceStore(
  env: string,
  traceStoreProvider: AsyncProvider<TraceStore>
) {
  traceStoresByEnv()[env] = traceStoreProvider;
}

const traceStoresByEnvCache: Record<any, Promise<TraceStore>> = {};

/**
 * Looks up the trace store for the given environment.
 */
export async function lookupTraceStore(
  env: string
): Promise<TraceStore | undefined> {
  if (!traceStoresByEnv()[env]) {
    return undefined;
  }
  const cached = traceStoresByEnvCache[env];
  if (!cached) {
    const newStore = traceStoresByEnv()[env]();
    traceStoresByEnvCache[env] = newStore;
    return newStore;
  }
  return cached;
}

/**
 * Registers a flow state store provider for the given environment.
 */
export function registerFlowStateStore(
  env: string,
  flowStateStoreProvider: AsyncProvider<FlowStateStore>
) {
  flowStateStoresByEnv()[env] = flowStateStoreProvider;
}

const flowStateStoresByEnvCache: Record<any, Promise<FlowStateStore>> = {};
/**
 * Looks up the flow state store for the given environment.
 */
export async function lookupFlowStateStore(
  env: string
): Promise<FlowStateStore | undefined> {
  if (!flowStateStoresByEnv()[env]) {
    return undefined;
  }
  const cached = flowStateStoresByEnvCache[env];
  if (!cached) {
    const newStore = flowStateStoresByEnv()[env]();
    flowStateStoresByEnvCache[env] = newStore;
    return newStore;
  }
  return cached;
}

/**
 * Registers a flow state store for the given environment.
 */
export function registerPluginProvider(name: string, provider: PluginProvider) {
  let cached;
  pluginsByName()[name] = {
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

export function lookupPlugin(name: string) {
  return pluginsByName()[name];
}

/**
 *
 */
export async function initializePlugin(name: string) {
  if (pluginsByName()[name]) {
    return await pluginsByName()[name].initializer();
  }
  return undefined;
}

export function registerSchema(
  name: string,
  data: { schema?: z.ZodTypeAny; jsonSchema?: JSONSchema }
) {
  schemasByName()[name] = data;
}

export function lookupSchema(name: string) {
  return schemasByName()[name];
}

/**
 * Development mode only. Starts a Reflection API so that the actions can be called by the Runner.
 */
if (process.env.GENKIT_ENV === 'dev') {
  startReflectionApi();
}

export function __hardResetRegistryForTesting() {
  delete global[ACTIONS_BY_ID];
  delete global[TRACE_STORES_BY_ENV];
  delete global[FLOW_STATE_STORES_BY_ENV];
  delete global[PLUGINS_BY_NAME];
  deleteAll(flowStateStoresByEnvCache);
  deleteAll(traceStoresByEnvCache);
}

function deleteAll(map: Record<any, any>) {
  Object.keys(map).forEach((key) => delete map[key]);
}
