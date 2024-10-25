import { GenerateResponse, GenerateResponseChunk } from '../generate';
import type { Formatter } from './types';

export const textParser: Formatter = (request) => {
  return {
    parseChunk: (chunk: GenerateResponseChunk, emit: (chunk: any) => void) => {
      emit(chunk.text);
    },

    parseResponse: (response: GenerateResponse) => {
      return response.text;
    },
  };
};
