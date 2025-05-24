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

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import type {
  Resource,
  ResourceTemplate,
} from '@modelcontextprotocol/sdk/types.js';
import { Genkit, z } from 'genkit';

function listResourcesTool(
  ai: Genkit,
  client: Client,
  params: { name: string; serverName?: string; asDynamicTool?: boolean }
) {
  const actionMetadata = {
    name: `${params.name}/list_resources`,
    description: `list all available resources for '${params.name}'`,
    inputSchema: z.object({
      /** Provide a cursor for accessing additional paginated results. */
      cursor: z.string().optional(),
      /** When specified, automatically paginate and fetch all resources. */
      all: z.boolean().optional(),
    }),
  };
  const fn = async ({ cursor, all }: { cursor?: string; all?: boolean }) => {
    if (!all) {
      return client.listResources();
    }

    let currentCursor: string | undefined = cursor;
    const resources: Resource[] = [];
    while (true) {
      const { nextCursor, resources: newResources } =
        await client.listResources({ cursor: currentCursor });
      resources.push(...newResources);
      currentCursor = nextCursor;
      if (!currentCursor) break;
    }
    return { resources };
  };

  return !!params.asDynamicTool
    ? ai.dynamicTool(actionMetadata, fn)
    : ai.defineTool(actionMetadata, fn);
}

function listResourceTemplatesTool(
  ai: Genkit,
  client: Client,
  params: { name: string; serverName?: string; asDynamicTool?: boolean }
) {
  const actionMetadata = {
    name: `${params.name}/list_resource_templates`,
    description: `list all available resource templates for '${params.name}'`,
    inputSchema: z.object({
      /** Provide a cursor for accessing additional paginated results. */
      cursor: z.string().optional(),
      /** When specified, automatically paginate and fetch all resources. */
      all: z.boolean().optional(),
    }),
  };

  const fn = async ({ cursor, all }: { cursor?: string; all?: boolean }) => {
    if (!all) {
      return client.listResourceTemplates();
    }

    let currentCursor: string | undefined = cursor;
    const resourceTemplates: ResourceTemplate[] = [];
    while (true) {
      const { nextCursor, resourceTemplates: newResourceTemplates } =
        await client.listResourceTemplates({ cursor: currentCursor });
      resourceTemplates.push(...newResourceTemplates);
      currentCursor = nextCursor;
      if (!currentCursor) break;
    }
    return { resourceTemplates };
  };

  return !!params.asDynamicTool
    ? ai.dynamicTool(actionMetadata, fn)
    : ai.defineTool(actionMetadata, fn);
}

function readResourceTool(
  ai: Genkit,
  client: Client,
  params: { name: string; serverName?: string; asDynamicTool?: boolean }
) {
  const actionMetadata = {
    name: `${params.name}/read_resource`,
    description: `this tool can read resources from '${params.name}'`,
    inputSchema: z.object({
      uri: z.string().describe('the URI of the resource to retrieve'),
    }),
  };
  const fn = async ({ uri }) => {
    return client.readResource({ uri });
  };

  return !!params.asDynamicTool
    ? ai.dynamicTool(actionMetadata, fn)
    : ai.defineTool(actionMetadata, fn);
}

/**
 * Fetches and returns Genkit dynamic tool actions for MCP resource operations.
 * This includes tools for listing resources, listing resource templates, and reading a resource.
 * These tools are created as dynamic tools, meaning they are not permanently defined
 * on the Genkit instance but are returned as executable actions.
 *
 * @param ai The Genkit instance, used for creating the dynamic tools.
 * @param client The MCP client instance to interact with the server.
 * @param params Configuration parameters, including the client name and server name for namespacing.
 * @returns An array of Genkit `ToolAction` instances for MCP resource operations.
 */
export function fetchDynamicResourceTools(
  ai: Genkit,
  client: Client,
  params: { name: string; serverName?: string }
) {
  const dynamicParams = { ...params, asDynamicTool: true };
  return [
    listResourcesTool(ai, client, dynamicParams),
    listResourceTemplatesTool(ai, client, dynamicParams),
    readResourceTool(ai, client, dynamicParams),
  ];
}
