import { extractJson } from '../extract';
import type { Formatter } from './types';

export const jsonParser: Formatter = (request) => {
  let accumulatedText: string = '';
  let instructions: boolean | string = false;

  if (request.output?.schema) {
    instructions = `Output should be in JSON format and conform to the following schema:

\`\`\`
${JSON.stringify(request.output!.schema!)}
\`\`\`
`;
  }

  return {
    parseChunk: (chunk, emit) => {
      accumulatedText = chunk.accumulatedText;
      emit(extractJson(accumulatedText));
    },

    parseResponse: (response) => {
      return extractJson(response.text);
    },

    instructions,
  };
};
