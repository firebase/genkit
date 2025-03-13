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

import { Dotprompt } from 'dotprompt';
import { AsyncLocalStorage } from 'node:async_hooks';
import * as z from 'zod';
import { Action, runOutsideActionRuntimeContext } from './action.js';
import { GenkitError } from './error.js';
import { logger } from './logging.js';
import { PluginProvider } from './plugin.js';
import { JSONSchema, toJsonSchema } from './schema.js';

export type AsyncProvider<T> = () => Promise<T>;

/**
 * Type of a runnable action.
 */
export type ActionType =
  | 'custom'
  | 'embedder'
  | 'evaluator'
  | 'executable-prompt'
  | 'flow'
  | 'indexer'
  | 'model'
  | 'prompt'
  | 'reranker'
  | 'retriever'
  | 'tool'
  | 'util';

/**
 * A schema is either a Zod schema or a JSON schema.
 */
export interface Schema {
  schema?: z.ZodTypeAny;
  jsonSchema?: JSONSchema;
}

function parsePluginName(registryKey: string) {
  const tokens = registryKey.split('/');
  if (tokens.length >= 4) {
    return tokens[2];
  }
  return undefined;
}

type ActionsRecord = Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>>;

/**
 * The registry is used to store and lookup actions, trace stores, flow state stores, plugins, and schemas.
 */
export class Registry {
  private actionsById: Record<
    string,
    | Action<z.ZodTypeAny, z.ZodTypeAny>
    | PromiseLike<Action<z.ZodTypeAny, z.ZodTypeAny>>
  > = {};
  private pluginsByName: Record<string, PluginProvider> = {};
  private schemasByName: Record<string, Schema> = {};
  private valueByTypeAndName: Record<string, Record<string, any>> = {};
  private allPluginsInitialized = false;
  public apiStability: 'stable' | 'beta' = 'stable';

  readonly asyncStore = new AsyncStore();
  readonly dotprompt = new Dotprompt({
    schemaResolver: async (name) => {
      const resolvedSchema = await this.lookupSchema(name);
      if (!resolvedSchema) {
        throw new GenkitError({
          message: `Schema '${name}' not found`,
          status: 'NOT_FOUND',
        });
      }
      return toJsonSchema(resolvedSchema);
    },
  });

  constructor(public parent?: Registry) {}

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
    return (
      ((await this.actionsById[key]) as R) || this.parent?.lookupAction(key)
    );
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
    logger.debug(`registering ${key}`);
    if (this.actionsById.hasOwnProperty(key)) {
      // TODO: Make this an error!
      logger.warn(
        `WARNING: ${key} already has an entry in the registry. Overwriting.`
      );
    }
    this.actionsById[key] = action;
  }

  /**
   * Registers an action promise in the registry.
   */
  registerActionAsync<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
    type: ActionType,
    name: string,
    action: PromiseLike<Action<I, O>>
  ) {
    const key = `/${type}/${name}`;
    logger.debug(`registering ${key} (async)`);
    if (this.actionsById.hasOwnProperty(key)) {
      // TODO: Make this an error!
      logger.warn(
        `WARNING: ${key} already has an entry in the registry. Overwriting.`
      );
    }
    this.actionsById[key] = action;
  }

  /**
   * Returns all actions in the registry.
   * @returns All actions in the registry.
   */
  async listActions(): Promise<ActionsRecord> {
    await this.initializeAllPlugins();
    const actions: Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>> = {};
    await Promise.all(
      Object.entries(this.actionsById).map(async ([key, action]) => {
        actions[key] = await action;
      })
    );
    return {
      ...(await this.parent?.listActions()),
      ...actions,
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
      return await runOutsideActionRuntimeContext(this, () =>
        this.pluginsByName[name].initializer()
      );
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

  registerValue(type: string, name: string, value: any) {
    if (!this.valueByTypeAndName[type]) {
      this.valueByTypeAndName[type] = {};
    }
    this.valueByTypeAndName[type][name] = value;
  }

  async lookupValue<T = unknown>(
    type: string,
    key: string
  ): Promise<T | undefined> {
    const pluginName = parsePluginName(key);
    if (!this.valueByTypeAndName[type]?.[key] && pluginName) {
      await this.initializePlugin(pluginName);
    }
    return (
      (this.valueByTypeAndName[type]?.[key] as T) ||
      this.parent?.lookupValue(type, key)
    );
  }

  async listValues<T>(type: string): Promise<Record<string, T>> {
    await this.initializeAllPlugins();
    return {
      ...((await this.parent?.listValues(type)) || {}),
      ...(this.valueByTypeAndName[type] || {}),
    } as Record<string, T>;
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

/**
 * Manages AsyncLocalStorage instances in a single place.
 */
export class AsyncStore {
  private asls: Record<string, AsyncLocalStorage<any>> = {};

  getStore<T>(key: string): T | undefined {
    return this.asls[key]?.getStore();
  }

  run<T, R>(key: string, store: T, callback: () => R): R {
    if (!this.asls[key]) {
      this.asls[key] = new AsyncLocalStorage<T>();
    }
    return this.asls[key].run(store, callback);
  }
}

/**
 * An object that has a reference to Genkit Registry.
 */
export interface HasRegistry {
  get registry(): Registry;
}
