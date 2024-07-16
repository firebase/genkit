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

import { AsyncLocalStorage } from 'node:async_hooks';
import * as z from 'zod';
import { Action } from './action.js';
import { FlowStateStore } from './flowTypes.js';
import { logger } from './logging.js';
import { PluginProvider } from './plugin.js';
import { startReflectionApi } from './reflectionApi.js';
import { JSONSchema } from './schema.js';
import { TraceStore } from './tracing/types.js';

export type AsyncProvider<T> = () => Promise<T>;

const REGISTRY_KEY = 'genkit__REGISTRY';

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
export function lookupAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  R extends Action<I, O>,
>(key: string): Promise<R> {
  return getRegistryInstance().lookupAction(key);
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
  return getRegistryInstance().registerAction(type, action);
}

type ActionsRecord = Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>>;

/**
 * Returns all actions in the registry.
 */
export function listActions(): Promise<ActionsRecord> {
  return getRegistryInstance().listActions();
}

/**
 * Registers a trace store provider for the given environment.
 */
export function registerTraceStore(
  env: string,
  traceStoreProvider: AsyncProvider<TraceStore>
) {
  return getRegistryInstance().registerTraceStore(env, traceStoreProvider);
}

/**
 * Looks up the trace store for the given environment.
 */
export function lookupTraceStore(env: string): Promise<TraceStore | undefined> {
  return getRegistryInstance().lookupTraceStore(env);
}

/**
 * Registers a flow state store provider for the given environment.
 */
export function registerFlowStateStore(
  env: string,
  flowStateStoreProvider: AsyncProvider<FlowStateStore>
) {
  return getRegistryInstance().registerFlowStateStore(
    env,
    flowStateStoreProvider
  );
}

/**
 * Looks up the flow state store for the given environment.
 */
export async function lookupFlowStateStore(
  env: string
): Promise<FlowStateStore | undefined> {
  return getRegistryInstance().lookupFlowStateStore(env);
}

/**
 * Registers a flow state store for the given environment.
 */
export function registerPluginProvider(name: string, provider: PluginProvider) {
  return getRegistryInstance().registerPluginProvider(name, provider);
}

export function lookupPlugin(name: string) {
  return getRegistryInstance().lookupFlowStateStore(name);
}

/**
 * Initialize plugin -- calls the plugin initialization function.
 */
export async function initializePlugin(name: string) {
  return getRegistryInstance().initializePlugin(name);
}

export function registerSchema(
  name: string,
  data: { schema?: z.ZodTypeAny; jsonSchema?: JSONSchema }
) {
  return getRegistryInstance().registerSchema(name, data);
}

export function lookupSchema(name: string) {
  return getRegistryInstance().lookupSchema(name);
}

/**
 * Development mode only. Starts a Reflection API so that the actions can be called by the Runner.
 */
if (process.env.GENKIT_ENV === 'dev') {
  startReflectionApi();
}

export function __hardResetRegistryForTesting() {
  delete global[REGISTRY_KEY];
  global[REGISTRY_KEY] = new Registry();
}

export class Registry {
  private actionsById: Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>> = {};
  private traceStoresByEnv: Record<string, AsyncProvider<TraceStore>> = {};
  private flowStateStoresByEnv: Record<string, AsyncProvider<FlowStateStore>> =
    {};
  private pluginsByName: Record<string, PluginProvider> = {};
  private schemasByName: Record<
    string,
    { schema?: z.ZodTypeAny; jsonSchema?: JSONSchema }
  > = {};

  private traceStoresByEnvCache: Record<any, Promise<TraceStore>> = {};
  private flowStateStoresByEnvCache: Record<any, Promise<FlowStateStore>> = {};
  private allPluginsInitialized = false;

  constructor(public parent?: Registry) {}

  static withParent(parent: Registry) {
    return new Registry(parent);
  }

  async lookupAction<
    I extends z.ZodTypeAny,
    O extends z.ZodTypeAny,
    R extends Action<I, O>,
  >(key: string): Promise<R> {
    return (await this._lookupAction(key)) || this.parent?.lookupAction(key);
  }

  private async _lookupAction<
    I extends z.ZodTypeAny,
    O extends z.ZodTypeAny,
    R extends Action<I, O>,
  >(key: string): Promise<R> {
    // If we don't see the key in the registry we try to initialize the plugin first.
    const pluginName = parsePluginName(key);
    if (!this.actionsById[key] && pluginName) {
      await this.initializePlugin(pluginName);
    }
    return this.actionsById[key] as R;
  }

  registerAction<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
    type: ActionType,
    action: Action<I, O>
  ) {
    logger.info(`Registering ${type}: ${action.__action.name}`);
    const key = `/${type}/${action.__action.name}`;
    if (this.actionsById.hasOwnProperty(key)) {
      logger.warn(
        `WARNING: ${key} already has an entry in the registry. Overwriting.`
      );
    }
    this.actionsById[key] = action;
  }

  async listActions(): Promise<ActionsRecord> {
    await this.initializeAllPlugins();
    return {
      ...(await this.parent?.listActions()),
      ...this.actionsById,
    };
  }

  async initializeAllPlugins() {
    if (this.allPluginsInitialized) {
      return;
    }
    for (const pluginName of Object.keys(this.pluginsByName)) {
      await initializePlugin(pluginName);
    }
    this.allPluginsInitialized = true;
  }
  

  registerTraceStore(
    env: string,
    traceStoreProvider: AsyncProvider<TraceStore>
  ) {
    this.traceStoresByEnv[env] = traceStoreProvider;
  }

  async lookupTraceStore(env: string): Promise<TraceStore | undefined> {
    return (
      (await this._lookupTraceStore(env)) || this.parent?.lookupTraceStore(env)
    );
  }

  private async _lookupTraceStore(
    env: string
  ): Promise<TraceStore | undefined> {
    if (!this.traceStoresByEnv[env]) {
      return undefined;
    }
    const cached = this.traceStoresByEnvCache[env];
    if (!cached) {
      const newStore = this.traceStoresByEnv[env]();
      this.traceStoresByEnvCache[env] = newStore;
      return newStore;
    }
    return cached;
  }

  registerFlowStateStore(
    env: string,
    flowStateStoreProvider: AsyncProvider<FlowStateStore>
  ) {
    this.flowStateStoresByEnv[env] = flowStateStoreProvider;
  }

  async lookupFlowStateStore(env: string): Promise<FlowStateStore | undefined> {
    return (
      (await this._lookupFlowStateStore(env)) ||
      this.parent?.lookupFlowStateStore(env)
    );
  }

  private async _lookupFlowStateStore(
    env: string
  ): Promise<FlowStateStore | undefined> {
    if (!this.flowStateStoresByEnv[env]) {
      return undefined;
    }
    const cached = this.flowStateStoresByEnvCache[env];
    if (!cached) {
      const newStore = this.flowStateStoresByEnv[env]();
      this.flowStateStoresByEnvCache[env] = newStore;
      return newStore;
    }
    return cached;
  }

  registerPluginProvider(name: string, provider: PluginProvider) {
    this.allPluginsInitialized = false;
    let cached;
    let isInitialized = false;
    this.pluginsByName[name] = {
      name: provider.name,
      initializer: () => {
        if (isInitialized) {
          return cached;
        }
        cached = provider.initializer();
        isInitialized = true;
        return cached;
      },
    };
    }

  lookupPlugin(name: string) {
    return this.pluginsByName[name] || this.parent?.lookupPlugin(name);
  }

  async initializePlugin(name: string) {
    if (this.pluginsByName[name]) {
      return await this.pluginsByName[name].initializer();
    }
    return undefined;
  }

  registerSchema(
    name: string,
    data: { schema?: z.ZodTypeAny; jsonSchema?: JSONSchema }
  ) {
    this.schemasByName[name] = data;
  }

  lookupSchema(name: string) {
    return this.schemasByName[name] || this.parent?.lookupSchema(name);
  }
}

// global regustry instance
global[REGISTRY_KEY] = new Registry();

const registryAls = new AsyncLocalStorage<Registry>();

/**
 * Executes provided function with within the provided registry.
 */
export function runWithRegistry<O>(registry: Registry, fn: () => O): O {
  return registryAls.run(registry, fn);
}

/**
 * Returns the current registry instance:
 *  - if running within `runWithRegistry` then return that registry
 *  - else return the global registry.
 */
export function getRegistryInstance(): Registry {
  return registryAls.getStore() || global[REGISTRY_KEY];
}
