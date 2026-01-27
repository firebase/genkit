/**
 * Copyright 2024 Bloom Labs Inc
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

import type Anthropic from '@anthropic-ai/sdk';
import type { CacheControlEphemeral } from '@anthropic-ai/sdk/resources/messages';
import { z } from 'genkit';
import { GenerationCommonConfigSchema } from 'genkit/model';

export type { CacheControlEphemeral as AnthropicCacheControl };

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

export const AnthropicBaseConfigSchema = GenerationCommonConfigSchema.extend({
  tool_choice: z
    .union([
      z
        .object({
          type: z.literal('auto'),
        })
        .passthrough(),
      z
        .object({
          type: z.literal('any'),
        })
        .passthrough(),
      z
        .object({
          type: z.literal('tool'),
          name: z.string(),
        })
        .passthrough(),
    ])
    .describe(
      'The tool choice to use for the request. This can be used to specify the tool to use for the request. If not specified, the model will choose the tool to use.'
    )
    .optional(),
  metadata: z
    .object({
      user_id: z.string().optional(),
    })
    .describe('The metadata to include in the request.')
    .passthrough()
    .optional(),
  /** Optional shorthand to pick API surface for this request. */
  apiVersion: z
    .enum(['stable', 'beta'])
    .optional()
    .describe(
      'The API version to use for the request. Both stable and beta features are available on the beta API surface.'
    ),
}).passthrough();

export type AnthropicBaseConfigSchemaType = typeof AnthropicBaseConfigSchema;

export const ThinkingConfigSchema = z
  .object({
    enabled: z.boolean().optional(),
    budgetTokens: z.number().min(1_024).optional(),
  })
  .passthrough()
  .passthrough()
  .superRefine((value, ctx) => {
    if (!value.enabled) return;

    if (value.budgetTokens === undefined) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['budgetTokens'],
        message: 'budgetTokens is required when thinking is enabled',
      });
    } else if (
      value.budgetTokens !== undefined &&
      !Number.isInteger(value.budgetTokens)
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['budgetTokens'],
        message: 'budgetTokens must be an integer',
      });
    }
  });

export const AnthropicThinkingConfigSchema = AnthropicBaseConfigSchema.extend({
  thinking: ThinkingConfigSchema.optional().describe(
    'The thinking configuration to use for the request. Thinking is a feature that allows the model to think about the request and provide a better response.'
  ),
}).passthrough();

export const AnthropicConfigSchema = AnthropicThinkingConfigSchema;

export type ThinkingConfig = z.infer<typeof ThinkingConfigSchema>;
export type AnthropicBaseConfig = z.infer<typeof AnthropicBaseConfigSchema>;
export type AnthropicThinkingConfig = z.infer<
  typeof AnthropicThinkingConfigSchema
>;
export type ClaudeConfig = AnthropicThinkingConfig | AnthropicBaseConfig;

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
  cfg: AnthropicThinkingConfig | AnthropicBaseConfig | undefined,
  pluginDefaultApiVersion?: 'stable' | 'beta'
): boolean {
  if (cfg?.apiVersion !== undefined) {
    return cfg.apiVersion === 'beta';
  }
  if (pluginDefaultApiVersion === 'beta') return true;
  return false;
}

/** Plain text document source. */
export interface AnthropicTextSource {
  type: 'text';
  data: string;
  mediaType?: string;
}

/** Base64-encoded document source (e.g., PDF). */
export interface AnthropicBase64Source {
  type: 'base64';
  data: string;
  mediaType: string;
}

/** File reference source (from Files API). */
export interface AnthropicFileSource {
  type: 'file';
  fileId: string;
}

/** Custom content blocks for granular citation control. */
export interface AnthropicContentSource {
  type: 'content';
  content: Array<
    | { type: 'text'; text: string }
    | {
        type: 'image';
        source: { type: 'base64'; mediaType: string; data: string };
      }
  >;
}

/** URL source for PDFs. */
export interface AnthropicURLSource {
  type: 'url';
  url: string;
}

/** Union of all document source types. */
export type AnthropicDocumentSource =
  | AnthropicTextSource
  | AnthropicBase64Source
  | AnthropicFileSource
  | AnthropicContentSource
  | AnthropicURLSource;

/** Options for creating an Anthropic document with optional citations. */
export interface AnthropicDocumentOptions {
  source: AnthropicDocumentSource;
  title?: string;
  context?: string;
  citations?: { enabled: boolean };
}

/** Citation from a plain text document (character indices). */
export interface CharLocationCitation {
  type: 'char_location';
  citedText: string;
  documentIndex: number;
  documentTitle?: string;
  fileId?: string;
  startCharIndex: number;
  endCharIndex: number;
}

/** Citation from a PDF document (page numbers). */
export interface PageLocationCitation {
  type: 'page_location';
  citedText: string;
  documentIndex: number;
  documentTitle?: string;
  fileId?: string;
  startPageNumber: number;
  endPageNumber: number;
}

/** Citation from a custom content document (block indices). */
export interface ContentBlockLocationCitation {
  type: 'content_block_location';
  citedText: string;
  documentIndex: number;
  documentTitle?: string;
  fileId?: string;
  startBlockIndex: number;
  endBlockIndex: number;
}

/** Union of all citation types for documents. */
export type AnthropicCitation =
  | CharLocationCitation
  | PageLocationCitation
  | ContentBlockLocationCitation;
