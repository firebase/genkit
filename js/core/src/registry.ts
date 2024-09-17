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

import { AsyncLocalStorage } from 'async_hooks';
import * as z from 'zod';
import { Action } from './action.js';
import { PluginProvider } from './plugin.js';
import { JSONSchema } from './schema.js';
import { TraceStore } from './tracing/types.js';

export type AsyncProvider<T> = () => Promise<T>;

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
  | 'util'
  | 'tool'
  | 'reranker';

/**
 * A schema is either a Zod schema or a JSON schema.
 */
export interface Schema {
  schema?: z.ZodTypeAny;
  jsonSchema?: JSONSchema;
}

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
 * Initialize all plugins in the registry.
 */
export async function initializeAllPlugins() {
  await getRegistryInstance().initializeAllPlugins();
}

/**
 * Returns all actions in the registry.
 */
export function listActions(): Promise<ActionsRecord> {
  return getRegistryInstance().listActions();
}

/**
 * Registers a trace store provider for the given environment.
 * @param env The environment to register the trace store for.
 * @param traceStoreProvider The trace store provider.
 */
export function registerTraceStore(
  env: string,
  traceStoreProvider: AsyncProvider<TraceStore>
) {
  return getRegistryInstance().registerTraceStore(env, traceStoreProvider);
}

/**
 * Looks up the trace store for the given environment.
 * @param env The environment to lookup the trace store for.
 * @returns The trace store.
 */
export function lookupTraceStore(env: string): Promise<TraceStore | undefined> {
  return getRegistryInstance().lookupTraceStore(env);
}

/**
 * Registers a plugin provider.
 * @param name The name of the plugin to register.
 * @param provider The plugin provider.
 */
export function registerPluginProvider(name: string, provider: PluginProvider) {
  return getRegistryInstance().registerPluginProvider(name, provider);
}

/**
 * Looks up a plugin.
 * @param name The name of the plugin to lookup.
 * @returns The plugin.
 */
export function lookupPlugin(name: string) {
  return getRegistryInstance().lookupPlugin(name);
}

/**
 * Initializes a plugin that has already been registered.
 * @param name The name of the plugin to initialize.
 * @returns The plugin.
 */
export async function initializePlugin(name: string) {
  return getRegistryInstance().initializePlugin(name);
}

/**
 * Registers a schema.
 * @param name The name of the schema to register.
 * @param data The schema to register (either a Zod schema or a JSON schema).
 */
export function registerSchema(name: string, data: Schema) {
  return getRegistryInstance().registerSchema(name, data);
}

/**
 * Looks up a schema.
 * @param name The name of the schema to lookup.
 * @returns The schema.
 */
export function lookupSchema(name: string) {
  return getRegistryInstance().lookupSchema(name);
}

const registryAls = new AsyncLocalStorage<Registry>();

/**
 * @returns The active registry instance.
 */
export function getRegistryInstance(): Registry {
  const registry = registryAls.getStore();
  if (!registry) {
    throw new Error('getRegistryInstance() called before runWithRegistry()');
  }
  return registry;
}

/**
 * Runs a function with a specific registry instance.
 * @param registry The registry instance to use.
 * @param fn The function to run.
 */
export function runWithRegistry<R>(registry: Registry, fn: () => R) {
  return registryAls.run(registry, fn);
}

/**
 * The registry is used to store and lookup actions, trace stores, flow state stores, plugins, and schemas.
 */
export class Registry {
  private actionsById: Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>> = {};
  private traceStoresByEnv: Record<string, AsyncProvider<TraceStore>> = {};
  private pluginsByName: Record<string, PluginProvider> = {};
  private schemasByName: Record<string, Schema> = {};
  private traceStoresByEnvCache: Record<any, Promise<TraceStore>> = {};
  private allPluginsInitialized = false;

  constructor(public parent?: Registry) {}

  /**
   * Creates a new registry overlaid onto the currently active registry.
   * @returns The new overlaid registry.
   */
  static withCurrent() {
    return new Registry(getRegistryInstance());
  }

  /**
   * Creates a new registry overlaid onto the provided registry.
   * @param parent The parent registry.
   * @returns The new overlaid registry.
   */
  static withParent(parent: Registry) {
    return new Registry(parent);
  }

  /**
   * Looks up an action in the registry.
   * @param key The key of the action to lookup.
   * @returns The action.
   */
  async lookupAction<
    I extends z.ZodTypeAny,
    O extends z.ZodTypeAny,
    R extends Action<I, O>,
  >(key: string): Promise<R> {
    // If we don't see the key in the registry we try to initialize the plugin first.
    const pluginName = parsePluginName(key);
    if (!this.actionsById[key] && pluginName) {
      await this.initializePlugin(pluginName);
    }
    return (this.actionsById[key] as R) || this.parent?.lookupAction(key);
  }

  /**
   * Registers an action in the registry.
   * @param type The type of the action to register.
   * @param action The action to register.
   */
  registerAction<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
    type: ActionType,
    action: Action<I, O>
  ) {
    const key = `/${type}/${action.__action.name}`;
    if (this.actionsById.hasOwnProperty(key)) {
      throw new Error(`Action ${key} already registered`);
    }
    this.actionsById[key] = action;
  }

  /**
   * Returns all actions in the registry.
   * @returns All actions in the registry.
   */
  async listActions(): Promise<ActionsRecord> {
    await this.initializeAllPlugins();
    return {
      ...(await this.parent?.listActions()),
      ...this.actionsById,
    };
  }

  /**
   * Initializes all plugins in the registry.
   */
  async initializeAllPlugins() {
    if (this.allPluginsInitialized) {
      return;
    }
    for (const pluginName of Object.keys(this.pluginsByName)) {
      await this.initializePlugin(pluginName);
    }
    this.allPluginsInitialized = true;
  }

  /**
   * Registers a trace store for the given environment.
   * @param env The environment to register the trace store for.
   * @param traceStoreProvider The trace store provider.
   */
  registerTraceStore(
    env: string,
    traceStoreProvider: AsyncProvider<TraceStore>
  ) {
    if (this.traceStoresByEnv[env]) {
      throw new Error(`Trace store for environment ${env} already registered`);
    }
    this.traceStoresByEnv[env] = traceStoreProvider;
  }

  /**
   * Looks up the trace store for the given environment.
   * @param env The environment to lookup the trace store for.
   * @returns The trace store.
   */
  async lookupTraceStore(env: string): Promise<TraceStore | undefined> {
    return (
      (await this.lookupOverlaidTraceStore(env)) ||
      this.parent?.lookupTraceStore(env)
    );
  }

  /**
   * Looks up the trace store for the given environment.
   * @param env The environment to lookup the trace store for.
   * @returns The trace store.
   */
  private async lookupOverlaidTraceStore(
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

  /**
   * Registers a plugin provider. This plugin must be initialized before it can be used by calling {@link initializePlugin} or {@link initializeAllPlugins}.
   * @param name The name of the plugin to register.
   * @param provider The plugin provider.
   */
  registerPluginProvider(name: string, provider: PluginProvider) {
    if (this.pluginsByName[name]) {
      throw new Error(`Plugin ${name} already registered`);
    }
    this.allPluginsInitialized = false;
    let cached;
    let isInitialized = false;
    this.pluginsByName[name] = {
      name: provider.name,
      initializer: () => {
        if (!isInitialized) {
          cached = provider.initializer();
          isInitialized = true;
        }
        return cached;
      },
    };
  }

  /**
   * Looks up a plugin.
   * @param name The name of the plugin to lookup.
   * @returns The plugin provider.
   */
  lookupPlugin(name: string): PluginProvider | undefined {
    return this.pluginsByName[name] || this.parent?.lookupPlugin(name);
  }

  /**
   * Initializes a plugin already registered with {@link registerPluginProvider}.
   * @param name The name of the plugin to initialize.
   * @returns The plugin.
   */
  async initializePlugin(name: string) {
    if (this.pluginsByName[name]) {
      return await this.pluginsByName[name].initializer();
    }
  }

  /**
   * Registers a schema.
   * @param name The name of the schema to register.
   * @param data The schema to register (either a Zod schema or a JSON schema).
   */
  registerSchema(name: string, data: Schema) {
    if (this.schemasByName[name]) {
      throw new Error(`Schema ${name} already registered`);
    }
    this.schemasByName[name] = data;
  }

  /**
   * Looks up a schema.
   * @param name The name of the schema to lookup.
   * @returns The schema.
   */
  lookupSchema(name: string): Schema | undefined {
    return this.schemasByName[name] || this.parent?.lookupSchema(name);
  }
}
