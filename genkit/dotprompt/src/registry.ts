import { config } from '@google-genkit/common/config';
import { lookupAction, registerAction } from '@google-genkit/common/registry';
import { Prompt, PromptAction } from './prompt';
import { readFileSync } from 'fs';
import logger from '@google-genkit/common/logging';
import { join } from 'path';

export function lookupPrompt(name: string, variant?: string): Prompt {
  const registryPrompt = lookupAction(
    `/prompt/${name}${variant ? `.${variant}` : ''}`
  ) as PromptAction;
  if (registryPrompt) return Prompt.fromAction(registryPrompt);

  const prompt = loadPrompt(name, variant);
  registerAction(
    'prompt',
    `/prompt/${name}${variant ? `.${variant}` : ''}`,
    prompt.action()
  );
  return prompt;
}

function loadPrompt(name: string, variant?: string) {
  const dir = config.options.promptDir || './prompts';
  try {
    const source = readFileSync(
      join(dir, `${name}${variant ? `.${variant}` : ''}.prompt`),
      'utf8'
    );
    const prompt = Prompt.parse(name, source);
    prompt.variant = variant;
    return prompt;
  } catch (e) {
    if (variant) {
      logger.warn(
        `Prompt '${name}.${variant}' not found, trying '${name}' without variant.`
      );
      return loadPrompt(name);
    }
    throw new Error(`Prompt ${name}${variant ? `.${variant}` : ''} not found`);
  }
}
