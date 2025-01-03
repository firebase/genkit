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
import { genkit, z } from 'genkit';
import assert from 'node:assert';
import { describe, it } from 'node:test';
import { ollama } from '../src/index.js';
import { OllamaPluginParams } from '../src/types.js';

// Utility function to parse command-line arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const serverAddress =
    args.find((arg) => arg.startsWith('--server-address='))?.split('=')[1] ||
    'http://localhost:11434';
  const modelName =
    args.find((arg) => arg.startsWith('--model-name='))?.split('=')[1] ||
    'phi3.5:latest';
  return { serverAddress, modelName };
}

const { serverAddress, modelName } = parseArgs();

// Define a schema for testing
const CountrySchema = z.object({
  name: z.string(),
  capital: z.string(),
  languages: z.array(z.string()),
});

describe('Ollama Structured Output - Live Tests', () => {
  const options: OllamaPluginParams = {
    serverAddress,
    models: [{ name: modelName, type: 'chat' }],
  };

  it('should handle structured output in chat mode', async () => {
    const ai = genkit({
      plugins: [ollama(options)],
    });

    const response = await ai.generate({
      model: `ollama/${modelName}`,
      messages: [
        {
          role: 'system',
          content: [
            {
              text: 'You are a helpful assistant that provides information about countries in a structured format.',
            },
          ],
        },
        {
          role: 'user',
          content: [{ text: 'Tell me about Canada.' }],
        },
      ],
      output: {
        format: 'json',
        schema: CountrySchema,
      },
    });

    assert.notEqual(response.message, undefined);
    assert.notEqual(response.message!.content, undefined);
    assert.notEqual(response.message!.content[0].text, undefined);

    const content = response.output!;

    // Validate the structure
    assert(typeof content.name === 'string');
    assert(typeof content.capital === 'string');
    assert(Array.isArray(content.languages));
    content.languages.forEach((lang) => {
      assert(typeof lang === 'string');
    });

    // Log the actual response for inspection
    console.log('Structured Response:', content);
  });

  it('should handle multiple requests with different schemas', async () => {
    const ai = genkit({
      plugins: [ollama(options)],
    });

    const PersonSchema = z.object({
      name: z.string(),
      age: z.number(),
      occupation: z.string(),
    });

    const response = await ai.generate({
      model: `ollama/${modelName}`,
      messages: [
        {
          role: 'user',
          content: [{ text: 'Create a profile for a fictional person.' }],
        },
      ],
      output: {
        format: 'json',
        schema: PersonSchema,
      },
    });

    assert.notEqual(response.message, undefined);
    const content = response.output!;

    // Validate the structure
    assert(typeof content.name === 'string');
    assert(typeof content.age === 'number');
    assert(typeof content.occupation === 'string');

    console.log('Person Response:', content);
  });
});
