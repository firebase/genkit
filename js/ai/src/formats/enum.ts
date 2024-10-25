import { GenkitError } from '@genkit-ai/core';
import type { Formatter } from './types';

export const enumParser: Formatter = (request) => {
  const schemaType = request.output?.schema?.type;
  if (schemaType && schemaType !== 'string' && schemaType !== 'enum') {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: `Must supply a 'string' or 'enum' schema type when using the enum parser format.`,
    });
  }

  let instructions: boolean | string = false;
  if (request.output?.schema?.enum) {
    instructions = `Output should be ONLY one of the following enum values. Do not output any additional information or add quotes.\n\n${request.output?.schema?.enum.map((v) => v.toString()).join('\n')}`;
  }

  return {
    parseResponse: (response) => {
      return response.text.trim();
    },
    instructions,
  };
};
