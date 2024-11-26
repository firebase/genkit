import type { Client } from '@modelcontextprotocol/sdk/client/index.js' with { 'resolution-mode': 'import' };
import type {
  Resource,
  ResourceTemplate,
} from '@modelcontextprotocol/sdk/types.js' with { 'resolution-mode': 'import' };
import { Genkit, z } from 'genkit';
import type { McpClientOptions } from '../index.js';

export function registerResourceTools(
  ai: Genkit,
  client: Client,
  params: McpClientOptions
) {
  ai.defineTool(
    {
      name: `${params.name}/list_resources`,
      description: `list all available resources for '${params.name}'`,
      inputSchema: z.object({
        /** Provide a cursor for accessing additional paginated results. */
        cursor: z.string().optional(),
        /** When specified, automatically paginate and fetch all resources. */
        all: z.boolean().optional(),
      }),
    },
    async ({ cursor, all }) => {
      if (!all) {
        return client.listResources();
      }

      let currentCursor: string | undefined;
      const resources: Resource[] = [];
      while (true) {
        const { nextCursor, resources: newResources } =
          await client.listResources({ cursor });
        resources.push(...newResources);
        currentCursor = nextCursor;
        if (!currentCursor) break;
      }
      return { resources };
    }
  );

  ai.defineTool(
    {
      name: `${params.name}/list_resource_templates`,
      description: `list all available resource templates for '${params.name}'`,
      inputSchema: z.object({
        /** Provide a cursor for accessing additional paginated results. */
        cursor: z.string().optional(),
        /** When specified, automatically paginate and fetch all resources. */
        all: z.boolean().optional(),
      }),
    },
    async ({ cursor, all }) => {
      if (!all) {
        return client.listResourceTemplates();
      }

      let currentCursor: string | undefined;
      const resourceTemplates: ResourceTemplate[] = [];
      while (true) {
        const { nextCursor, resourceTemplates: newResourceTemplates } =
          await client.listResourceTemplates({ cursor });
        resourceTemplates.push(...newResourceTemplates);
        currentCursor = nextCursor;
        if (!currentCursor) break;
      }
      return { resourceTemplates };
    }
  );

  ai.defineTool(
    {
      name: `${params.name}/read_resource`,
      description: `this tool can read resources from '${params.name}'`,
      inputSchema: z.object({
        uri: z.string().describe('the URI of the resource to retrieve'),
      }),
    },
    async ({ uri }) => {
      return client.readResource({ uri });
    }
  );
}
