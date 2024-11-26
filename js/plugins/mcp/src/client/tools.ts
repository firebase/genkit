import type { Client } from '@modelcontextprotocol/sdk/client/index.js' with { 'resolution-mode': 'import' };
import type {
  CallToolResult,
  Tool,
} from '@modelcontextprotocol/sdk/types.js' with { 'resolution-mode': 'import' };
import { Genkit, z } from 'genkit';
import { logger } from 'genkit/logging';
import type { McpClientOptions } from '../index.js';

const toText = (c: CallToolResult['content']) =>
  c.map((p) => p.text || '').join('');

function processResult(result: CallToolResult) {
  if (result.isError) return { error: toText(result.content) };
  if (result.content.every((c) => !!c.text)) {
    const text = toText(result.content);
    if (text.trim().startsWith('{') || text.trim().startsWith('[')) {
      try {
        return JSON.parse(text);
      } catch (e) {
        return text;
      }
    }
    return text;
  }
  if (result.content.length === 1) return result.content[0];
  return result;
}

function registerTool(
  ai: Genkit,
  client: Client,
  tool: Tool,
  params: McpClientOptions
) {
  logger.debug(
    `[@genkit-ai/mcp] Registering MCP tool ${params.name}/${tool.name}`
  );
  ai.defineTool(
    {
      name: tool.name,
      description: tool.description || '',
      inputJsonSchema: tool.inputSchema,
      outputSchema: z.any(),
    },
    async (args) => {
      logger.debug(
        `[@genkit-ai/mcp] Calling MCP tool ${params.name}/${tool.name} with arguments`,
        JSON.stringify(args)
      );
      const result = await client.callTool({
        name: tool.name,
        arguments: args,
      });
      logger.debug(
        `MCP tool ${tool.name} result:`,
        JSON.stringify(result, null, 2)
      );
      if (params.rawToolResponses) return result;
      return processResult(result as CallToolResult);
    }
  );
}

/**
 * Lookup all tools available in the server and register each as a Genkit tool.
 */
export async function registerAllTools(
  ai: Genkit,
  client: Client,
  params: McpClientOptions
): Promise<void> {
  let cursor: string | undefined;
  while (true) {
    const { nextCursor, tools } = await client.listTools({ cursor });
    tools.forEach((t) => registerTool(ai, client, t, params));
    cursor = nextCursor;
    if (!cursor) break;
  }
}
