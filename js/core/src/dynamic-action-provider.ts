/**
 * Copyright 2025 Google LLC
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

import type * as z from 'zod';
import { Action, ActionMetadata, defineAction } from './action.js';
import { ActionType, Registry } from './registry.js';

type DapValue = {
  [K in ActionType]?: Action<z.ZodTypeAny, z.ZodTypeAny, z.ZodTypeAny>[];
};

class SimpleCache {
  private value: DapValue | undefined;
  private expiresAt: number | undefined;
  private ttlMillis: number;
  private dap: DynamicActionProviderAction;
  private dapFn: DapFn;
  private fetchPromise: Promise<DapValue> | null = null;

  constructor(
    dap: DynamicActionProviderAction,
    config: DapConfig,
    dapFn: DapFn
  ) {
    this.dap = dap;
    this.dapFn = dapFn;
    this.ttlMillis = !config.cacheConfig?.ttlMillis
      ? 3 * 1000
      : config.cacheConfig?.ttlMillis;
  }

  async getOrFetch(): Promise<DapValue> {
    const isStale =
      !this.value ||
      !this.expiresAt ||
      this.ttlMillis < 0 ||
      Date.now() > this.expiresAt;
    if (!isStale) {
      return this.value!;
    }

    if (!this.fetchPromise) {
      this.fetchPromise = (async () => {
        try {
          // Get a new value
          this.value = await this.dapFn(); // this returns the actual actions
          this.expiresAt = Date.now() + this.ttlMillis;

          // Also run the action
          this.dap.run(this.value); // This returns metadata and shows up in dev UI

          return this.value;
        } catch (error) {
          console.error('Error fetching Dynamic Action Provider value:', error);
          this.invalidate();
          throw error; // Rethrow to reject the fetchPromise
        } finally {
          // Allow new fetches after this one completes or fails.
          this.fetchPromise = null;
        }
      })();
    }
    return await this.fetchPromise;
  }

  invalidate() {
    this.value = undefined;
  }
}

export interface DynamicRegistry {
  __cache: SimpleCache;
  invalidateCache(): void;
  getAction(
    actionType: string,
    actionName: string
  ): Promise<Action<z.ZodTypeAny, z.ZodTypeAny, z.ZodTypeAny> | undefined>;
  listActionMetadata(
    actionType: string,
    actionName: string
  ): Promise<ActionMetadata[]>;
}

export type DynamicActionProviderAction = Action<
  z.ZodTypeAny,
  z.ZodTypeAny,
  z.ZodTypeAny
> &
  DynamicRegistry & {
    __action: {
      metadata: {
        type: 'dynamic-action-provider';
      };
    };
  };

export function isDynamicActionProvider(
  obj: Action<z.ZodTypeAny, z.ZodTypeAny>
): obj is DynamicActionProviderAction {
  return obj.__action?.metadata?.type == 'dynamic-action-provider';
}

export interface DapConfig {
  name: string;
  description?: string;
  cacheConfig?: {
    // Negative = no caching
    // Zero or undefined = default (3000 milliseconds)
    // Positive number = how many milliseconds the cache is valid for
    ttlMillis: number | undefined;
  };
  metadata?: Record<string, any>;
}

export type DapFn = () => Promise<DapValue>;
export type DapMetadata = {
  [K in ActionType]?: ActionMetadata[];
};

function transformDapValue(value: DapValue): DapMetadata {
  const metadata: DapMetadata = {};
  for (const key of Object.keys(value)) {
    metadata[key] = value[key].map((a) => {
      return a.__action;
    });
  }
  return metadata;
}

export function defineDynamicActionProvider(
  registry: Registry,
  config: DapConfig | string,
  fn: DapFn
): DynamicActionProviderAction {
  let cfg: DapConfig;
  if (typeof config == 'string') {
    cfg = { name: config };
  } else {
    cfg = { ...config };
  }
  const a = defineAction(
    registry,
    {
      ...cfg,
      actionType: 'dynamic-action-provider',
      metadata: { ...(cfg.metadata || {}), type: 'dynamic-action-provider' },
    },
    async (i, _options) => {
      // The actions are retrieved and saved in a cache and then passed in here.
      // We run this action to return the metadata for the actions only.
      // We pass the actions in here to prevent duplicate calls to the mcp
      // and also so we are guaranteed the same actions since there is only a
      // single call to mcp client/host.
      return transformDapValue(i);
    }
  );
  implementDap(a as DynamicActionProviderAction, cfg, fn);
  return a as DynamicActionProviderAction;
}

function implementDap(
  dap: DynamicActionProviderAction,
  config: DapConfig,
  dapFn: DapFn
) {
  dap.__cache = new SimpleCache(dap, config, dapFn);
  dap.invalidateCache = () => {
    dap.__cache.invalidate();
  };

  dap.getAction = async (actionType: string, actionName: string) => {
    const result = await dap.__cache.getOrFetch();
    if (result[actionType]) {
      return result[actionType].find((t) => t.__action.name == actionName);
    }
    return undefined;
  };

  dap.listActionMetadata = async (actionType: string, actionName: string) => {
    const result = await dap.__cache.getOrFetch();
    if (!result[actionType]) {
      return [];
    }

    // Match everything in the actionType
    const metadata = result[actionType].map((a) => a.__action);
    if (actionName == '*') {
      return metadata;
    }

    // Prefix matching
    if (actionName.endsWith('*')) {
      const prefix = actionName.slice(0, -1);
      return metadata.filter((m) => m.name.startsWith(prefix));
    }

    // Single match or empty array
    return metadata.filter((m) => m.name == actionName);
  };
}
