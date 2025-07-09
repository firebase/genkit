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

import { RuntimeManager } from '@genkit-ai/tools-common/manager';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp';
import z from 'zod';

export function defineFlowTools(server: McpServer, manager: RuntimeManager) {
  server.registerTool(
    'list_flows',
    {
      title: 'List Genkit Flows',
      description:
        'Use this to discover available Genkit flows or inspect the input schema of Genkit flows to know how to successfully call them.',
    },
    async () => {
      const actions = await manager.listActions();

      let flows = '';
      for (const key of Object.keys(actions)) {
        if (key.startsWith('/flow/')) {
          flows += ' - Flow name: ' + key.substring('/flow/'.length) + '\n';
          if (actions[key].description) {
            flows += '   Description: ' + actions[key].description + '\n';
          }
          flows +=
            '   Input schema: ' +
            JSON.stringify(actions[key].inputSchema, undefined, 2) +
            '\n\n';
        }
      }

      return { content: [{ type: 'text', text: flows }] };
    }
  );

  server.registerTool(
    'run_flow',
    {
      title: 'Run Flow',
      description: 'Runs the flow with the provided input',
      inputSchema: {
        flowName: z.string().describe('name of the flow'),
        input: z
          .string()
          .describe(
            'Flow input as JSON object encoded as string (it will be passed through `JSON.parse`). Must conform to the schema.'
          )
          .optional(),
      },
    },
    async ({ flowName, input }) => {
      try {
        const response = await manager.runAction({
          key: `/flow/${flowName}`,
          input: input !== undefined ? JSON.parse(input) : undefined,
        });
        return {
          content: [
            { type: 'text', text: JSON.stringify(response, undefined, 2) },
          ],
        };
      } catch (e) {
        return {
          content: [{ type: 'text', text: `Error: ${e}` }],
        };
      }
    }
  );
}
