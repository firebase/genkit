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

import { ActionRunOptions, GenkitError, z } from '@genkit-ai/core';
import type { Registry } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import { GenerateAPI } from '../generate-api.js';
import type { GenerateActionOptions } from '../model-types.js';
import { type MiddlewareRef } from '../model-types.js';
import {
  GenerateRequest,
  GenerateResponseData,
  ToolRequestPart,
  ToolResponsePart,
} from '../model.js';
import { type GenkitPluginV2 } from '../plugin.js';
import { ToolAction } from '../tool.js';

/** Descriptor for a registered middleware, returned by reflection API. */
export const MiddlewareDescSchema = z.object({
  /** Unique name of the middleware. */
  name: z.string(),
  /** Human-readable description of what the middleware does. */
  description: z.string().optional(),
  /** JSON Schema for the middleware's configuration. */
  configSchema: z.record(z.any()).nullish(),
  /** User defined metadata for the middleware. */
  metadata: z.record(z.any()).nullish(),
});
export type MiddlewareDesc = z.infer<typeof MiddlewareDescSchema>;

/**
 * Defines a Genkit Generate Middleware instance, which can be configured and registered.
 * When invoked with an optional configuration, it returns a reference suitable for
 * inclusion in a `GenerateOptions.use` array.
 */
export interface GenerateMiddleware<C extends z.ZodTypeAny = z.ZodTypeAny>
  extends MiddlewareDesc {
  /** Configures the middleware, returning a MiddlewareRef for usage in `generate({use: [...]})`. */
  (config?: z.infer<C>): MiddlewareRef & { __def: GenerateMiddleware<C> };
  /** The unique name of this middleware. */
  name: string;
  /** An optional description of what the middleware does. */
  description?: string;
  /** An optional Zod schema for validating the middleware's configuration. */
  configSchema?: C;
  /** Metadata describing this middleware. */
  metadata?: Record<string, any>;
  /**
   * Factory function that receives the validated configuration and creates
   * a `GenerateMiddlewareDef` holding the active hooks.
   */
  instantiate: (
    config: z.infer<C> | undefined,
    ai: GenerateAPI
  ) => GenerateMiddlewareDef;
  /**
   * Optional plugin wrapper exposing this middleware for framework-level registration.
   */
  plugin: (config?: z.infer<C>) => GenkitPluginV2;
  /** Generates a JSON-compatible representation of the middleware metadata. */
  toJson: () => MiddlewareDesc;
}

/**
 * An instantiated implementation of a Generate Middleware.
 * Provides optional hooks to intercept the high-level `generate` action,
 * the underlying `model` execution, or individual `tool` calls, as well as
 * tools to inject into the execution.
 */
export interface GenerateMiddlewareDef {
  /**
   * Hook for intercepting the top-level generate action.
   * Can be used to inject request parameters, modify the response, or catch errors.
   */
  generate?: (
    req: GenerateActionOptions,
    ctx: ActionRunOptions<any>,
    next: (
      req: GenerateActionOptions,
      ctx: ActionRunOptions<any>
    ) => Promise<GenerateResponseData>
  ) => Promise<GenerateResponseData>;
  /**
   * Hook for intercepting the underlying model execution.
   * Ideal for model-level caching, retry logic, or prompt/response parsing.
   */
  model?: (
    req: GenerateRequest<any>,
    ctx: ActionRunOptions<any>,
    next: (
      req: GenerateRequest<any>,
      ctx: ActionRunOptions<any>
    ) => Promise<GenerateResponseData>
  ) => Promise<GenerateResponseData>;
  /**
   * Hook for intercepting individual tool calls.
   * Enables caching tool responses, validating inputs, or overriding tool execution.
   */
  tool?: (
    req: ToolRequestPart,
    ctx: ActionRunOptions<any>,
    next: (
      req: ToolRequestPart,
      ctx: ActionRunOptions<any>
    ) => Promise<{
      response?: ToolResponsePart;
      interrupt?: ToolRequestPart;
      preamble?: GenerateActionOptions;
    }>
  ) => Promise<{
    response?: ToolResponsePart;
    interrupt?: ToolRequestPart;
    preamble?: GenerateActionOptions;
  }>;
  /**
   * Tools to statically inject into the generation request whenever this middleware is active.
   */
  tools?: ToolAction[];
}

export function generateMiddleware<
  ConfigSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(
  options: {
    name: string;
    configSchema?: ConfigSchema;
    description?: string;
    metadata?: Record<string, any>;
  },
  middlewareFn: (
    config: z.infer<ConfigSchema> | undefined,
    ai: GenerateAPI
  ) => GenerateMiddlewareDef
): GenerateMiddleware<ConfigSchema> {
  const def = function (config?: z.infer<ConfigSchema>) {
    return {
      name: options.name,
      config,
      __def: def,
    };
  } as GenerateMiddleware<ConfigSchema>;

  Object.defineProperty(def, 'name', { value: options.name });
  def.configSchema = options.configSchema;
  def.description = options.description;
  def.metadata = options.metadata;
  def.instantiate = middlewareFn;
  def.plugin = (pluginConfig?: z.infer<ConfigSchema>) => ({
    name: `middleware:${options.name}`,
    version: 'v2',
    generateMiddleware: () => {
      if (pluginConfig === undefined) {
        return [def];
      }
      const wrappedDef = function (config?: z.infer<ConfigSchema>) {
        return def(config ?? pluginConfig);
      } as GenerateMiddleware<ConfigSchema>;

      Object.defineProperty(wrappedDef, 'name', { value: options.name });
      wrappedDef.configSchema = options.configSchema;
      wrappedDef.description = options.description;
      wrappedDef.metadata = options.metadata;
      wrappedDef.instantiate = (reqConfig, ai) =>
        def.instantiate(reqConfig ?? pluginConfig, ai);
      wrappedDef.plugin = def.plugin;

      return [wrappedDef];
    },
    model: (_) => {
      throw new Error('Not supported for middleware plugins');
    },
  });

  def.toJson = () => ({
    name: options.name,
    description: options.description,
    configSchema: options.configSchema
      ? toJsonSchema({ schema: options.configSchema })
      : undefined,
    metadata: options.metadata,
  });

  return def;
}

export async function resolveMiddleware(
  registry: Registry,
  refs?: MiddlewareRef[]
): Promise<GenerateMiddlewareDef[]> {
  const result: GenerateMiddlewareDef[] = [];
  if (!refs) return result;
  for (const ref of refs) {
    const def = await registry.lookupValue<GenerateMiddleware>(
      'middleware',
      ref.name
    );
    if (!def) {
      throw new GenkitError({
        status: 'NOT_FOUND',
        message: `Middleware ${ref.name} not found in registry.`,
      });
    }
    result.push(def.instantiate(ref.config, new GenerateAPI(registry)));
  }
  return result;
}
