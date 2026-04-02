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

import * as fs from 'fs';
import { generateMiddleware, z, type GenerateMiddleware } from 'genkit';
import { tool } from 'genkit/beta';
import * as path from 'path';

export const SkillsOptionsSchema = z.object({
  skillPaths: z.array(z.string()).optional(),
});

export type SkillsOptions = z.infer<typeof SkillsOptionsSchema>;

/**
 * Creates a middleware that scans for skills in specified paths.
 * Injects a system prompt listing available skills and provides a `use_skill` tool.
 */
export const skills: GenerateMiddleware<typeof SkillsOptionsSchema> =
  generateMiddleware(
    {
      name: 'skills',
      configSchema: SkillsOptionsSchema,
    },
    ({ config }) => {
      const skillPaths = config?.skillPaths ?? ['skills'];
      const skillCache = new Map<
        string,
        { path: string; description: string }
      >();

      function parseFrontmatter(content: string) {
        const match = /^---\n([^]*?)\n---/.exec(content);
        if (!match) return null;

        const yaml = match[1];
        const nameMatch = /name:\s*(.+)/.exec(yaml);
        const descriptionMatch = /description:\s*(.+)/.exec(yaml);

        return {
          name: nameMatch ? nameMatch[1].trim() : undefined,
          description: descriptionMatch
            ? descriptionMatch[1].trim()
            : undefined,
        };
      }

      let scanned = false;

      async function ensureSkillsScanned() {
        if (scanned) return;
        scanned = true;
        skillCache.clear();

        for (const p of skillPaths) {
          const dirPath = path.resolve(p);
          if (!fs.existsSync(dirPath)) continue;

          const files = fs.readdirSync(dirPath, { withFileTypes: true });
          for (const file of files) {
            if (file.isDirectory() && !file.name.startsWith('.')) {
              const skillDir = path.join(dirPath, file.name);
              const skillMdPath = path.join(skillDir, 'SKILL.md');
              if (fs.existsSync(skillMdPath)) {
                let description = 'No description provided.';
                try {
                  const content = fs.readFileSync(skillMdPath, 'utf-8');
                  const fm = parseFrontmatter(content);
                  if (fm?.description) {
                    description = fm.description;
                  }
                } catch (e) {
                  // ignore
                }
                skillCache.set(file.name, {
                  path: skillMdPath,
                  description,
                });
              }
            }
          }
        }
      }

      const useSkillTool = tool(
        {
          name: 'use_skill',
          description: 'Use a skill by its name.',
          inputSchema: z.object({
            skillName: z.string().describe('The name of the skill to use.'),
          }),
          outputSchema: z.string(),
        },
        async (input) => {
          await ensureSkillsScanned();
          const info = skillCache.get(input.skillName);
          if (!info) {
            throw new Error(
              'Access denied: Path is outside of skills directory or skill not found.'
            );
          }

          try {
            return fs.readFileSync(info.path, 'utf-8');
          } catch (e) {
            throw new Error(`Failed to read skill "${input.skillName}": ${e}`);
          }
        }
      );

      return {
        tools: [useSkillTool],
        generate: async (req, ctx, next) => {
          await ensureSkillsScanned();
          if (skillCache.size === 0) return next(req, ctx);

          const skillsList = Array.from(skillCache.entries())
            .map(([name, info]) => {
              if (info.description !== 'No description provided.') {
                return ` - ${name} - ${info.description}`;
              }
              return ` - ${name}`;
            })
            .join('\n');

          const systemPromptText =
            `<skills>\n` +
            `You have access to a library of skills that serve as specialized instructions/personas.\n` +
            `Strongly prefer to use them when working on anything related to them.\n` +
            `Only use them once to load the context.\n` +
            `Here are the available skills:\n` +
            `${skillsList}\n` +
            `</skills>`;

          const messages = [...req.messages];
          let injectedPart: any | undefined;
          let injectedMsgIndex = -1;
          let injectedPartIndex = -1;

          for (let i = 0; i < messages.length; i++) {
            const msg = messages[i];
            for (let j = 0; j < msg.content.length; j++) {
              const p = msg.content[j];
              if (p.text && p.metadata?.['skills-instructions'] === true) {
                injectedPart = p;
                injectedMsgIndex = i;
                injectedPartIndex = j;
                break;
              }
            }
            if (injectedPart) break;
          }

          if (injectedPart) {
            if (injectedPart.text !== systemPromptText) {
              const newContent = [...messages[injectedMsgIndex].content];
              newContent[injectedPartIndex] = {
                text: systemPromptText,
                metadata: { 'skills-instructions': true },
              };
              messages[injectedMsgIndex] = {
                ...messages[injectedMsgIndex],
                content: newContent as any,
              };
            }
          } else {
            const systemMsgIndex = messages.findIndex(
              (m) => m.role === 'system'
            );
            if (systemMsgIndex !== -1) {
              messages[systemMsgIndex] = {
                ...messages[systemMsgIndex],
                content: [
                  ...messages[systemMsgIndex].content,
                  {
                    text: systemPromptText,
                    metadata: { 'skills-instructions': true },
                  },
                ],
              };
            } else {
              messages.unshift({
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

          return next({ ...req, messages }, ctx);
        },
      };
    }
  );
