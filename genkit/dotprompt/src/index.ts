import { readFileSync, readdirSync } from 'fs';
import { PromptFile } from './prompt';
export { PromptFile };
import fetch from 'node-fetch';
import { join } from 'path';

export function loadPromptFile(path: string): PromptFile {
  return PromptFile.parse(readFileSync(path, 'utf-8'));
}

export async function loadPromptUrl(url: string): Promise<PromptFile> {
  const response = await fetch(url);
  const text = await response.text();
  return PromptFile.parse(text);
}

export function loadPromptDir(path: string): Record<string, PromptFile> {
  const files = readdirSync(path);
  const prompts: Record<
    string,
    { name: string; file?: string; variants: Record<string, string> }
  > = {};

  for (const file of files) {
    if (!file.endsWith('.prompt')) continue;
    const parts = file.split('.');
    prompts[parts[0]] = prompts[parts[0]] || { name: parts[0], variants: {} };
    if (parts.length === 2) {
      prompts[parts[0]].file = file;
    } else if (parts.length === 3) {
      prompts[parts[0]].variants[parts[1]] = file;
    }
  }

  const out: Record<string, PromptFile> = {};
  for (const name in prompts) {
    const variants: Record<string, PromptFile> = {};
    for (const variant in prompts[name].variants) {
      variants[variant] = loadPromptFile(
        join(path, prompts[name].variants![variant])
      );
    }
    // skip if no baseline file
    if (!prompts[name].file) {
      continue;
    }

    out[name] = loadPromptFile(join(path, prompts[name].file!));
    out[name].variants = variants;
  }

  return out;
}
