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

import { existsSync, readFileSync } from 'fs';
import { gemini } from './ai-tools/gemini';
import { AIToolModule } from './types';

import { writeFile } from 'fs/promises';
import * as inquirer from 'inquirer';
/*
 * Deeply compares two JSON-serializable objects.
 * It's a simplified version of a deep equal function, sufficient for comparing the structure
 * of the gemini-extension.json file. It doesn't handle special cases like RegExp, Date, or functions.
 */
export function deepEqual(a: any, b: any): boolean {
  if (a === b) {
    return true;
  }

  if (
    typeof a !== 'object' ||
    a === null ||
    typeof b !== 'object' ||
    b === null
  ) {
    return false;
  }

  const keysA = Object.keys(a);
  const keysB = Object.keys(b);

  if (keysA.length !== keysB.length) {
    return false;
  }

  for (const key of keysA) {
    if (!keysB.includes(key) || !deepEqual(a[key], b[key])) {
      return false;
    }
  }

  return true;
}

export const AI_TOOLS: Record<string, AIToolModule> = {
  gemini,
};

export async function detectSupportedTools(): Promise<AIToolModule[]> {
  const tools: AIToolModule[] = [];
  for (const entry of Object.values(AI_TOOLS)) {
    if (entry.detect) {
      const detected = await entry.detect();
      if (detected) {
        tools.push(entry);
      }
    }
  }
  return tools;
}

/**
 * Replace an entire prompt file (no user content to preserve)
 * Used for files we fully own like Cursor and Gemini configs
 */
export async function initOrReplaceFile(
  filePath: string,
  content: string
): Promise<{ updated: boolean }> {
  const fileExists = existsSync(filePath);
  if (fileExists) {
    const currentConfig = readFileSync(filePath, 'utf-8');
    if (!deepEqual(currentConfig, content)) {
      await writeFile(filePath, content);
      return { updated: true };
    }
  } else {
    await writeFile(filePath, content);
    return { updated: true };
  }
  return { updated: false };
}

/**
 * Shows a confirmation prompt.
 */
export async function confirm(args: {
  default?: boolean;
  message?: string;
}): Promise<boolean> {
  const message = args.message ?? `Do you wish to continue?`;
  const answer = await inquirer.prompt({
    type: 'confirm',
    name: 'confirm',
    message,
    default: args.default,
  });
  return answer.confirm;
}
