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

import { Resource, ResourceTemplate } from '@modelcontextprotocol/sdk/types.js';
import { Genkit, GenkitError, ToolAction, z } from 'genkit';
import { logger } from 'genkit/logging';
import { GenkitMcpHost } from '../client';

function listResourcesTool(
  ai: Genkit,
  host: GenkitMcpHost,
  params: { asDynamicTool?: boolean }
): ToolAction {
  const actionMetadata = {
    name: `${host.name}/list_resources`,
    description: `list all available resources`,
    inputSchema: z
      .object({
        servers: z
          .array(z.string())
          .describe(
            'optional array of server names to list resources for. When not provided resources for all servers are returned.'
          )
          .optional(),
      })
      .optional(),
  };
  const fn = async (opts?: { servers?: string[] }) => {
    const resources: Record<
      string,
      { resources: Resource[]; resourceTemplates: ResourceTemplate[] }
    > = {};
    for (const client of host.activeClients) {
      if (
        opts?.servers &&
        opts.servers.length > 0 &&
        !opts.servers.includes(client.name)
      ) {
        continue;
      }
      resources[client.name] = {
        resources: [],
        resourceTemplates: [],
      };
      try {
        resources[client.name].resources = (
          await client._server!.client.listResources()
        ).resources;
      } catch (e) {
        logger.warn(`[MCP] failed to list resources for ${client.name}`, e);
      }
      try {
        resources[client.name].resourceTemplates = (
          await client._server!.client.listResourceTemplates()
        ).resourceTemplates;
      } catch (e) {
        logger.warn(
          `[MCP] failed to list resource templates for ${client.name}`,
          e
        );
      }
    }
    return { servers: resources };
  };

  return !!params.asDynamicTool
    ? ai.dynamicTool(actionMetadata, fn)
    : ai.defineTool(actionMetadata, fn);
}

function readResourceTool(
  ai: Genkit,
  host: GenkitMcpHost,
  params: { asDynamicTool?: boolean }
) {
  const actionMetadata = {
    name: `${host.name}/read_resource`,
    description: `this tool can read resources`,
    inputSchema: z.object({
      server: z.string(),
      uri: z.string().describe('the URI of the resource to retrieve'),
    }),
  };
  const fn = async ({ server, uri }) => {
    const client = host.activeClients.find((c) => c.serverName === server);
    if (!client) {
      throw new GenkitError({
        status: 'NOT_FOUND',
        message: `Server ${server} not found in the active server list.`,
      });
    }
    return client!._server!.client.readResource({ uri });
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
export function fetchDynamicResourceTools(ai: Genkit, host: GenkitMcpHost) {
  const dynamicParams = { asDynamicTool: true };
  return [
    listResourcesTool(ai, host, dynamicParams),
    readResourceTool(ai, host, dynamicParams),
  ];
}
