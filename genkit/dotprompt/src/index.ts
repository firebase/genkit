import { readFileSync } from 'fs';
import { PromptFile } from './prompt';
export { PromptFile };
import fetch from 'node-fetch';

export function loadPromptFile(path: string): PromptFile {
  return PromptFile.parse(readFileSync(path, 'utf-8'));
}

export async function loadPromptUrl(url: string): Promise<PromptFile> {
  const response = await fetch(url);
  const text = await response.text();
  return PromptFile.parse(text);
}
