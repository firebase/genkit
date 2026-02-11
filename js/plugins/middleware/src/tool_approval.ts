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

import { generateMiddleware, ToolInterruptError, z } from 'genkit';

export const ToolApprovalOptionsSchema = z.object({
  approved: z
    .array(z.string())
    .describe('List of approved tool names.')
    .optional(),
});

export type ToolApprovalOptions = z.infer<typeof ToolApprovalOptionsSchema>;

/**
 * Creates a middleware that checks if a tool is on the approved list.
 * If not, it throws a ToolInterruptError.
 */
export const toolApproval = generateMiddleware(
  {
    name: 'toolApproval',
    configSchema: ToolApprovalOptionsSchema,
  },
  (options, ai) => {
    const approvedTools = new Set(options?.approved || []);
    return {
      tool: async (req, ctx, next) => {
        if (
          req.metadata?.['tool-approved'] === true ||
          approvedTools.has(req.toolRequest.name)
        ) {
          return next(req, ctx);
        }

        await ai.run(
          `toolApproval:${req.toolRequest.name}`,
          req.toolRequest.input,
          async () => {
            throw new ToolInterruptError({
              toolName: req.toolRequest.name,
              reason: 'Tool not in approved list',
            });
          }
        );
      },
    };
  }
);
