import { GenkitError } from '@genkit-ai/core';
import { extractItems } from '../extract';
import type { Formatter } from './types';

export const arrayParser: Formatter = (request) => {
  if (request.output?.schema && request.output?.schema.type !== 'array') {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: `Must supply an 'array' schema type when using the 'items' parser format.`,
    });
  }

  let instructions: boolean | string = false;
  if (request.output?.schema) {
    instructions = `Output should be a JSON array conforming to the following schema:
    
    \`\`\`
    ${JSON.stringify(request.output!.schema!)}
    \`\`\`
    `;
  }

  let cursor: number = 0;

  return {
    parseChunk: (chunk, emit) => {
      const { items, cursor: newCursor } = extractItems(
        chunk.accumulatedText,
        cursor
      );

      // Emit any complete items
      for (const item of items) {
        emit(item);
      }

      // Update cursor position
      cursor = newCursor;
    },

    parseResponse: (response) => {
      const { items } = extractItems(response.text, 0);
      return items;
    },

    instructions,
  };
};
