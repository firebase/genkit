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
  ToolInterruptError,
  z,
  type GenerateMiddleware,
} from 'genkit';

export const ToolApprovalOptionsSchema = z.object({
  approved: z.array(z.string()).describe('List of approved tool names.'),
});

export type ToolApprovalOptions = z.infer<typeof ToolApprovalOptionsSchema>;

/**
 * Creates a middleware that restricts tool execution to an approved list.
 * Throws a `ToolInterruptError` if an unapproved tool is called, unless approved via metadata.
 */
export const toolApproval: GenerateMiddleware<
  typeof ToolApprovalOptionsSchema
> = generateMiddleware(
  {
    name: 'toolApproval',
    configSchema: ToolApprovalOptionsSchema,
  },
  ({ config }) => {
    const approvedTools = config?.approved ?? [];

    return {
      tool: async (req, ctx, next) => {
        const isApproved = (ctx as any).resumed?.toolApproved === true;

        if (!approvedTools.includes(req.toolRequest.name) && !isApproved) {
          throw new ToolInterruptError({
            message: `Tool not in approved list: ${req.toolRequest.name}`,
          });
        }

        return next(req, ctx);
      },
    };
  }
);
