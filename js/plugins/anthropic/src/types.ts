/**
 * Original work Copyright 2024 Bloom Labs Inc
 * Modifications Copyright 2025 Google LLC
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

import type Anthropic from '@anthropic-ai/sdk';
import { z } from 'genkit';
import { GenerationCommonConfigSchema } from 'genkit/model';

/**
 * Internal symbol for dependency injection in tests.
 * Not part of the public API.
 * @internal
 */
export const __testClient = Symbol('testClient');

/**
 * Plugin configuration options for the Anthropic plugin.
 */
export interface PluginOptions {
  apiKey?: string;
  cacheSystemPrompt?: boolean;
  /** Default API surface for all requests unless overridden per-request. */
  apiVersion?: 'stable' | 'beta';
}

/**
 * Internal plugin options that include test client injection.
 * @internal
 */
export interface InternalPluginOptions extends PluginOptions {
  [__testClient]?: Anthropic;
}

/**
 * Shared parameters required to construct Claude helpers.
 */
interface ClaudeHelperParamsBase {
  name: string;
  client: Anthropic;
  cacheSystemPrompt?: boolean;
  defaultApiVersion?: 'stable' | 'beta';
}

/**
 * Parameters for creating a Claude model action.
 */
export interface ClaudeModelParams extends ClaudeHelperParamsBase {}

/**
 * Parameters for creating a Claude runner.
 */
export interface ClaudeRunnerParams extends ClaudeHelperParamsBase {}

export const AnthropicConfigSchema = GenerationCommonConfigSchema.extend({
  tool_choice: z
    .union([
      z.object({
        type: z.literal('auto'),
      }),
      z.object({
        type: z.literal('any'),
      }),
      z.object({
        type: z.literal('tool'),
        name: z.string(),
      }),
    ])
    .optional(),
  metadata: z
    .object({
      user_id: z.string().optional(),
    })
    .optional(),
  /** Optional shorthand to pick API surface for this request. */
  apiVersion: z.enum(['stable', 'beta']).optional(),
});

/**
 * Media object representation with URL and optional content type.
 */
export interface Media {
  url: string;
  contentType?: string;
}

export const MediaSchema = z.object({
  url: z.string(),
  contentType: z.string().optional(),
});

export const MediaTypeSchema = z.enum([
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
]);

export type MediaType = z.infer<typeof MediaTypeSchema>;

export const MEDIA_TYPES = {
  JPEG: 'image/jpeg',
  PNG: 'image/png',
  GIF: 'image/gif',
  WEBP: 'image/webp',
} as const satisfies Record<string, MediaType>;

/**
 * Resolve whether beta API should be used for this call.
 * Priority:
 *   1. request.config.apiVersion (per-request override - explicit stable or beta)
 *   2. pluginDefaultApiVersion (plugin-wide default)
 *   3. otherwise stable
 */
export function resolveBetaEnabled(
  cfg: z.infer<typeof AnthropicConfigSchema> | undefined,
  pluginDefaultApiVersion?: 'stable' | 'beta'
): boolean {
  if (cfg?.apiVersion !== undefined) {
    return cfg.apiVersion === 'beta';
  }
  if (pluginDefaultApiVersion === 'beta') return true;
  return false;
}
