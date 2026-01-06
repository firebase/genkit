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

/**
 * MCP tool configuration for individual tools.
 */
export const McpToolConfigSchema = z
  .object({
    enabled: z
      .boolean()
      .optional()
      .describe('Whether this tool is enabled. Defaults to true.'),
    defer_loading: z
      .boolean()
      .optional()
      .describe(
        'If true, tool description is not sent to the model initially. Used with Tool Search Tool.'
      ),
  })
  .passthrough();

/**
 * MCP server configuration for connecting to remote MCP servers.
 */
export const McpServerConfigSchema = z
  .object({
    type: z
      .literal('url')
      .describe('Type of MCP server connection. Currently only "url" is supported.'),
    url: z
      .string()
      .url('MCP server URL must be a valid URL')
      .refine((url) => url.startsWith('https://'), {
        message: 'MCP server URL must use HTTPS protocol',
      })
      .describe('The URL of the MCP server. Must start with https://.'),
    name: z
      .string()
      .min(1, 'MCP server name cannot be empty')
      .describe(
        'A unique identifier for this MCP server. Must be referenced by exactly one MCPToolset.'
      ),
    authorization_token: z
      .string()
      .optional()
      .describe('OAuth authorization token if required by the MCP server.'),
  })
  .passthrough();

/**
 * MCP toolset configuration for exposing tools from an MCP server.
 */
export const McpToolsetSchema = z
  .object({
    type: z.literal('mcp_toolset').describe('Type must be "mcp_toolset".'),
    mcp_server_name: z
      .string()
      .describe('Must match a server name defined in the mcp_servers array.'),
    default_config: McpToolConfigSchema.optional().describe(
      'Default configuration applied to all tools. Individual tool configs will override these defaults.'
    ),
    configs: z
      .record(z.string(), McpToolConfigSchema)
      .optional()
      .describe(
        'Per-tool configuration overrides. Keys are tool names, values are configuration objects.'
      ),
  })
  .passthrough();

export type McpToolConfig = z.infer<typeof McpToolConfigSchema>;
export type McpServerConfig = z.infer<typeof McpServerConfigSchema>;
export type McpToolset = z.infer<typeof McpToolsetSchema>;

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
  /** MCP servers to connect to for server-managed tools (beta API only) */
  mcp_servers: z
    .array(McpServerConfigSchema)
    .optional()
    .describe(
      'List of MCP servers to connect to. Requires beta API (apiVersion: "beta").'
    ),
  /** MCP toolsets to expose from connected MCP servers (beta API only) */
  mcp_toolsets: z
    .array(McpToolsetSchema)
    .optional()
    .describe(
      'List of MCP toolsets to expose. Each toolset references an MCP server by name.'
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

/**
 * Validates MCP configuration:
 * - MCP server names must be unique
 * - MCP toolsets must reference servers defined in mcp_servers
 * - Each MCP server must be referenced by exactly one toolset
 */
function validateMcpConfig(
  config: z.infer<typeof AnthropicThinkingConfigSchema>,
  ctx: z.RefinementCtx
): void {
  // Validate MCP server name uniqueness
  if (config.mcp_servers && config.mcp_servers.length > 1) {
    const names = config.mcp_servers.map(
      (s: z.infer<typeof McpServerConfigSchema>) => s.name
    );
    const uniqueNames = new Set(names);
    if (uniqueNames.size !== names.length) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['mcp_servers'],
        message: 'MCP server names must be unique',
      });
    }
  }

  // Validate mcp_server_name references exist in mcp_servers
  if (config.mcp_toolsets && config.mcp_toolsets.length > 0) {
    const serverNames = new Set(
      config.mcp_servers?.map(
        (s: z.infer<typeof McpServerConfigSchema>) => s.name
      ) ?? []
    );
    config.mcp_toolsets.forEach(
      (toolset: z.infer<typeof McpToolsetSchema>, i: number) => {
        if (!serverNames.has(toolset.mcp_server_name)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['mcp_toolsets', i, 'mcp_server_name'],
            message: `MCP toolset references unknown server '${toolset.mcp_server_name}'. Available servers: ${[...serverNames].join(', ') || '(none)'}`,
          });
        }
      }
    );
  }

  // Validate each MCP server is referenced by exactly one toolset
  if (config.mcp_servers && config.mcp_servers.length > 0) {
    const toolsetReferences = new Map<string, number>();
    (config.mcp_toolsets ?? []).forEach(
      (t: z.infer<typeof McpToolsetSchema>) => {
        const count = toolsetReferences.get(t.mcp_server_name) ?? 0;
        toolsetReferences.set(t.mcp_server_name, count + 1);
      }
    );
    config.mcp_servers.forEach(
      (server: z.infer<typeof McpServerConfigSchema>, i: number) => {
        const refCount = toolsetReferences.get(server.name) ?? 0;
        if (refCount === 0) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['mcp_servers', i, 'name'],
            message: `MCP server '${server.name}' is not referenced by any toolset. Each server must be referenced by exactly one mcp_toolset.`,
          });
        } else if (refCount > 1) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['mcp_servers', i, 'name'],
            message: `MCP server '${server.name}' is referenced by ${refCount} toolsets. Each server must be referenced by exactly one mcp_toolset.`,
          });
        }
      }
    );
  }
}

export const AnthropicConfigSchema =
  AnthropicThinkingConfigSchema.superRefine(validateMcpConfig);

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
