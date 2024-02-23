import { readFileSync } from 'fs';
import { Prompt } from './prompt.js';
export { Prompt as PromptFile };
import { basename } from 'path';
import { lookupPrompt } from './registry.js';

export function loadPromptFile(path: string): Prompt {
  return Prompt.parse(
    basename(path).split('.')[0],
    readFileSync(path, 'utf-8')
  );
}

export async function loadPromptUrl(
  name: string,
  url: string
): Promise<Prompt> {
  const fetch = (await import('node-fetch')).default;
  const response = await fetch(url);
  const text = await response.text();
  return Prompt.parse(name, text);
}

export async function prompt<Variables = unknown>(
  name: string,
  options?: { variant?: string }
): Promise<Prompt<Variables>> {
  return lookupPrompt(name, options?.variant) as Prompt<Variables>;
}

export { Prompt, PromptOptions, PromptAction, PromptInput } from './prompt.js';
