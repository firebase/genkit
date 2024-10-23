/**
 * Copyright 2024 Google LLC
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

import { Candidate, GenerateOptions, GenerateResponse, GenerateResponseChunk } from './generate';
import { GenerateResponseChunkData } from './model';
import { extractJson } from './extract';
import { toJsonSchema, validateSchema } from '@genkit-ai/core/schema';

export type FormatParser<T = unknown> = {
  name: string;
  parseResponse: (res: GenerateResponse, candidateIdx?: number) => T;
  parseChunk?: (chunk: GenerateResponseChunk) => T | null;
  instructions?: (req: GenerateOptions) => string;
};

const findCandidate = (candidates: Candidate[], index?: number): Candidate => {
  if (candidates.length === 0) {
    throw new Error('No candidates found');
  }

  if (index !== undefined) {
    if (index < 0 || index >= candidates.length) {
      throw new Error(`Candidate index out of bounds: ${index}`);
    }
    return candidates[index];
  }

  return candidates.find(isValidCandidate) || candidates[0];
};

const isValidCandidate = (candidate: Candidate): boolean => {
  const jsonOutput = extractJson(candidate.text(), false);
  if (!jsonOutput) return false;

  const schema = candidate.request?.output?.schema;
  if (!schema) return true;

  return validateSchema(jsonOutput, { jsonSchema: schema }).valid;
};

const getAccumulatedChunksText = (accumulatedChunks?: GenerateResponseChunkData[]) => {
    if (!accumulatedChunks) return null;
    return accumulatedChunks
        .map((chunk) => chunk.content.map((part) => part.text || '').join(''))
        .join('');
}

const formatRegistry: Record<string, FormatParser> = {
  text: {
    name: 'text',
    parseResponse: (res, candidateIdx) => {
        const candidate = findCandidate(res.candidates, candidateIdx);
        return candidate.text() || null;
    },
    parseChunk: (chunk) => {
        return getAccumulatedChunksText(chunk.accumulatedChunks);
    },
  },
  json: {
    name: 'json',
    parseResponse: (res, candidateIdx) => {
        const candidate = findCandidate(res.candidates, candidateIdx);
        return extractJson(candidate.text(), true);
    },
    parseChunk: (chunk) => {
        const accumulatedText = getAccumulatedChunksText(chunk.accumulatedChunks);
        if (!accumulatedText) return null;
        return extractJson(accumulatedText, false);
    },
    instructions: (req) => {
      let jsonSchema = toJsonSchema({
        schema: req.output?.schema,
        jsonSchema: req.output?.jsonSchema,
      });
    
      return `Output should be in JSON format with the following schema:
${JSON.stringify(jsonSchema, null, 0)}`;
    },
  },
};

export function getAvailableFormats(): string[] {
  return Object.keys(formatRegistry);
}

export function defineFormat<T>(format: FormatParser<T>) {
  formatRegistry[format.name] = format;
}

export function getFormatParser(name: string): FormatParser | undefined {
  return formatRegistry[name];
}
