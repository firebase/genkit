/**
 * Copyright 2026 Google LLC
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

import {
  generateMiddleware,
  MessageData,
  z,
  type GenerateMiddleware,
} from 'genkit';
import * as path from 'path';
import { defineListFileTool } from './filesystem/list_files';
import { defineReadFileTool } from './filesystem/read_file';

export const FilesystemOptionsSchema = z.object({
  rootDirectory: z
    .string()
    .describe(
      'The root directory to which all filesystem operations are restricted.'
    ),
});

export type FilesystemOptions = z.infer<typeof FilesystemOptionsSchema>;

/**
 * Creates a middleware that grants the LLM basic readonly access to the filesystem.
 * Injects `list_files` and `read_file` tools restricted to the provided `rootDirectory`.
 */
export const filesystem: GenerateMiddleware<typeof FilesystemOptionsSchema> =
  generateMiddleware(
    {
      name: 'filesystem',
      configSchema: FilesystemOptionsSchema,
    },
    (options) => {
      if (!options?.rootDirectory) {
        throw new Error(
          'filesystem middleware requires a rootDirectory option'
        );
      }
      const rootDir = path.resolve(options.rootDirectory);

      function resolvePath(requestedPath: string) {
        const p = path.resolve(rootDir, requestedPath);
        // Ensure the resolved path starts with the rootDir and a path separator
        // to prevent directory traversal attacks (e.g. rootDir is /a/b, requested is ../b_secret)
        if (!p.startsWith(rootDir + path.sep) && p !== rootDir) {
          throw new Error('Access denied: Path is outside of root directory.');
        }
        return p;
      }

      const messageQueue: MessageData[] = [];

      const listFilesTool = defineListFileTool(resolvePath);
      const readFileTool = defineReadFileTool(messageQueue, resolvePath);

      const filesystemTools = [listFilesTool, readFileTool];
      const filesystemToolNames = filesystemTools.map((t) => t.__action.name);

      return {
        tools: filesystemTools,
        tool: async (req, ctx, next) => {
          try {
            return await next(req, ctx);
          } catch (e: any) {
            if (filesystemToolNames.includes(req.toolRequest.name)) {
              const errorPart = {
                text: `Tool '${req.toolRequest.name}' failed: ${
                  e.message || String(e)
                }`,
              };
              if (
                messageQueue.length > 0 &&
                messageQueue[messageQueue.length - 1].role === 'user'
              ) {
                messageQueue[messageQueue.length - 1].content.push(errorPart);
              } else {
                messageQueue.push({
                  role: 'user',
                  content: [errorPart],
                });
              }
              return;
            }
            throw e;
          }
        },
        generate: async (req, ctx, next) => {
          if (messageQueue.length > 0) {
            req.messages.push(...messageQueue);
            messageQueue.length = 0;
          }
          return await next(req, ctx);
        },
      };
    }
  );
