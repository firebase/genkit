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

import { record } from '@genkit-ai/tools-common/utils';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp';
import { z } from 'zod';
import { McpRunToolEvent } from './analytics.js';
import {
  McpRuntimeManager,
  getCommonSchema,
  resolveProjectRoot,
} from './util.js';

export function defineRuntimeTools(server: McpServer, projectRoot: string) {
  server.registerTool(
    'start_runtime',
    {
      title: 'Starts a Genkit runtime process',
      description: `Use this to start a Genkit runtime process (This is typically the entry point to the users app). Once started, the runtime will be picked up by the \`genkit start\` command to power the Dev UI features like model and flow playgrounds. The inputSchema for this tool matches the function prototype for \`NodeJS.child_process.spawn\`.
        
      Examples: 
        {command: 'go', args: ['run', 'main.go']}
        {command: 'npm', args: ['run', 'dev']}`,
      inputSchema: getCommonSchema({
        command: z.string().describe('The command to run'),
        args: z
          .array(z.string())
          .describe(
            'List of command line arguments. IMPORTANT: This must be an array of strings, not a single string.'
          ),
      }),
    },
    async (opts) => {
      await record(new McpRunToolEvent('start_runtime'));
      const rootOrError = resolveProjectRoot(opts, projectRoot);
      if (typeof rootOrError !== 'string') return rootOrError;

      await McpRuntimeManager.getManagerWithDevProcess(
        rootOrError,
        opts.command,
        opts.args
      );

      return {
        content: [{ type: 'text', text: `Done.` }],
      };
    }
  );

  const registerControlTool = (
    name: string,
    title: string,
    action: 'kill' | 'restart'
  ) => {
    server.registerTool(
      name,
      {
        title,
        description: `Use this to ${action} an existing runtime that was started using the \`start_runtime\` tool`,
        inputSchema: getCommonSchema(),
      },
      async (opts) => {
        await record(new McpRunToolEvent(name));
        const rootOrError = resolveProjectRoot(opts, projectRoot);
        if (typeof rootOrError !== 'string') return rootOrError;

        const runtimeManager = await McpRuntimeManager.getManager(rootOrError);
        if (!runtimeManager.processManager) {
          return {
            isError: true,
            content: [
              { type: 'text', text: `No runtime process currently running.` },
            ],
          };
        }

        await runtimeManager.processManager[action]();
        return {
          content: [{ type: 'text', text: `Done.` }],
        };
      }
    );
  };

  registerControlTool(
    'kill_runtime',
    'Kills any existing Genkit runtime process',
    'kill'
  );
  registerControlTool(
    'restart_runtime',
    'Restarts any existing Genkit runtime process',
    'restart'
  );
}
