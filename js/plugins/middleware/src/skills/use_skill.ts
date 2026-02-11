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

import * as fs from 'fs/promises';
import { ToolAction, z,  } from 'genkit';
import { tool } from 'genkit/beta';
import path from 'path';

export function defineUseSkillTool(
  resolvePath: (requestedPath: string) => string
): ToolAction {
  return tool(
    {
      name: 'use_skill',
      description: 'Use a skill by its name.',
      inputSchema: z.object({
        skillName: z.string().describe('The name of the skill to use.'),
      }),
      outputSchema: z.string(),
    },
    async (input) => {
      const targetFile = resolvePath(path.join(input.skillName, 'SKILL.md'));
      try {
        const content = await fs.readFile(targetFile, 'utf8');
        return content;
      } catch (e) {
        throw new Error(`Failed to read skill '${input.skillName}': ${e}`);
      }
    }
  );
}
