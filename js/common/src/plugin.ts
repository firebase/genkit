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

import { FlowStateStore } from './flowTypes';
import { TraceStore } from './tracing';
import { Action } from './types';
import { LoggerConfig, TelemetryConfig } from './telemetryTypes';
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
  telemetry?: {
    instrumentation?: Provider<TelemetryConfig>;
    logger?: Provider<LoggerConfig>;
  };
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
