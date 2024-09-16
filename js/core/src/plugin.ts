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

import { z } from 'zod';
import { Action } from './action.js';
import { FlowStateStore } from './flowTypes.js';
import { LoggerConfig, TelemetryConfig } from './telemetryTypes.js';
import { TraceStore } from './tracing.js';

export interface Provider<T> {
  id: string;
  value: T;
}

export interface PluginProvider {
  name: string;
  initializer: () =>
    | InitializedPlugin
    | void
    | Promise<InitializedPlugin | void>;
}

export interface InitializedPlugin {
  models?: Action<z.ZodTypeAny, z.ZodTypeAny>[];
  retrievers?: Action<z.ZodTypeAny, z.ZodTypeAny>[];
  embedders?: Action<z.ZodTypeAny, z.ZodTypeAny>[];
  indexers?: Action<z.ZodTypeAny, z.ZodTypeAny>[];
  evaluators?: Action<z.ZodTypeAny, z.ZodTypeAny>[];
  flowStateStore?: Provider<FlowStateStore> | Provider<FlowStateStore>[];
  traceStore?: Provider<TraceStore> | Provider<TraceStore>[];
  telemetry?: {
    instrumentation?: Provider<TelemetryConfig>;
    logger?: Provider<LoggerConfig>;
  };
}

type PluginInit = (
  ...args: any[]
) => InitializedPlugin | void | Promise<InitializedPlugin | void>;

export type Plugin<T extends any[]> = (...args: T) => PluginProvider;

/**
 * Defines a Genkit plugin.
 */
export function genkitPlugin<T extends PluginInit>(
  pluginName: string,
  initFn: T
): Plugin<Parameters<T>> {
  return (...args: Parameters<T>) => ({
    name: pluginName,
    initializer: async () => {
      const initializedPlugin = (await initFn(...args)) || {};
      validatePluginActions(pluginName, initializedPlugin);
      return initializedPlugin;
    },
  });
}

function validatePluginActions(pluginName: string, plugin?: InitializedPlugin) {
  if (!plugin) {
    return;
  }

  plugin.models?.forEach((model) => validateNaming(pluginName, model));
  plugin.retrievers?.forEach((retriever) =>
    validateNaming(pluginName, retriever)
  );
  plugin.embedders?.forEach((embedder) => validateNaming(pluginName, embedder));
  plugin.indexers?.forEach((indexer) => validateNaming(pluginName, indexer));
  plugin.evaluators?.forEach((evaluator) =>
    validateNaming(pluginName, evaluator)
  );
}

function validateNaming(
  pluginName: string,
  action: Action<z.ZodTypeAny, z.ZodTypeAny>
) {
  const nameParts = action.__action.name.split('/');
  if (nameParts[0] !== pluginName) {
    const err = `Plugin name ${pluginName} not found in action name ${action.__action.name}. Action names must follow the pattern {pluginName}/{actionName}`;
    throw new Error(err);
  }
}
