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

import type { ActionMetadata } from '@genkit-ai/core';
import type { Genkit } from './genkit.js';
import type { ActionType } from './registry.js';

export interface PluginProvider {
  name: string;
  initializer: () => void | Promise<void>;
  resolver?: (action: ActionType, target: string) => Promise<void>;
  listActions?: () => Promise<ActionMetadata[]>;
}

export type GenkitPlugin = (genkit: Genkit) => PluginProvider;

export type PluginInit = (genkit: Genkit) => void | Promise<void>;

export type PluginActionResolver = (
  genkit: Genkit,
  action: ActionType,
  target: string
) => Promise<void>;

/**
 * Defines a Genkit plugin.
 */
export function genkitPlugin<T extends PluginInit>(
  pluginName: string,
  initFn: T,
  resolveFn?: PluginActionResolver,
  listActionsFn?: () => Promise<ActionMetadata[]>
): GenkitPlugin {
  return (genkit: Genkit) => ({
    name: pluginName,
    initializer: async () => {
      await initFn(genkit);
    },
    resolver: async (action: ActionType, target: string): Promise<void> => {
      if (resolveFn) {
        return await resolveFn(genkit, action, target);
      }
    },
    listActions: async (): Promise<ActionMetadata[]> => {
      if (listActionsFn) {
        return await listActionsFn();
      }
      return [];
    },
  });
}
