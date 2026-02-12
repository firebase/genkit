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
import { generateMiddleware, z, type GenerateMiddleware } from 'genkit';
import * as path from 'path';
import { defineUseSkillTool } from './skills/use_skill.js';

export const SkillsOptionsSchema = z.object({
  skillsDirectory: z
    .string()
    .optional()
    .describe('The directory containing skill files. Defaults to "skills".'),
});

export type SkillsOptions = z.infer<typeof SkillsOptionsSchema>;

function parseFrontmatter(content: string) {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;
  const yaml = match[1];
  const nameMatch = yaml.match(/name:\s*(.+)/);
  const descriptionMatch = yaml.match(/description:\s*(.+)/);
  return {
    name: nameMatch ? nameMatch[1].trim() : undefined,
    description: descriptionMatch ? descriptionMatch[1].trim() : undefined,
  };
}

/**
 * Creates a middleware that injects available skills into the system prompt and provides a tool to use them.
 */
export const skills: GenerateMiddleware<typeof SkillsOptionsSchema> =
  generateMiddleware(
    {
      name: 'skills',
      configSchema: SkillsOptionsSchema,
    },
    (options) => {
      const skillsDir = path.resolve(options?.skillsDirectory || 'skills');

      function resolvePath(requestedPath: string) {
        const p = path.resolve(skillsDir, requestedPath);
        // Ensure the resolved path starts with the skillsDir and a path separator
        // to prevent directory traversal attacks
        if (!p.startsWith(skillsDir + path.sep) && p !== skillsDir) {
          throw new Error('Access denied: Path is outside of skills directory.');
        }
        return p;
      }

      const useSkillTool = defineUseSkillTool(resolvePath);

      return {
        tools: [useSkillTool],
        generate: async (req, ctx, next) => {
          const skillsList: string[] = [];
          try {
            const entries = await fs.readdir(skillsDir, {
              withFileTypes: true,
            });
            const skillDirs = entries.filter(
              (e) => e.isDirectory() && !e.name.startsWith('.')
            );

            for (const dir of skillDirs) {
              const skillPath = path.join(skillsDir, dir.name, 'SKILL.md');
              try {
                const content = await fs.readFile(skillPath, 'utf8');
                const fm = parseFrontmatter(content);
                if (fm && fm.description) {
                  skillsList.push(` - ${dir.name} - ${fm.description}`);
                } else {
                  skillsList.push(` - ${dir.name}`);
                }
              } catch (e) {
                // Skip if SKILL.md missing or unreadable
              }
            }
          } catch (e) {
            // If directory doesn't exist, we just don't list any skills.
          }

          if (skillsList.length > 0) {
            const skillsTag = '<skills>';
            const systemPromptText = `${skillsTag}
You have access to a library of skills that serve as specialized instructions/personas.
Strongly prefer to use them when working on anything related to them.
Only use them once to load the context.
Here are the available skills:
${skillsList.join('\n')}
</skills>`;

            let injectedPart;
            for (const msg of req.messages) {
              for (const part of msg.content) {
                if (part.metadata && part.metadata['skills-instructions']) {
                  injectedPart = part;
                  break;
                }
              }
              if (injectedPart) break;
            }

            if (injectedPart) {
              if (injectedPart.text !== systemPromptText) {
                injectedPart.text = systemPromptText;
              }
            } else {
              const systemMsg = req.messages.find((m) => m.role === 'system');
              if (systemMsg) {
                systemMsg.content.push({
                  text: systemPromptText,
                  metadata: { 'skills-instructions': true },
                });
              } else {
                req.messages.unshift({
                  role: 'system',
                  content: [
                    {
                      text: systemPromptText,
                      metadata: { 'skills-instructions': true },
                    },
                  ],
                });
              }
            }
          }

          return await next(req, ctx);
        },
      };
    }
  );
