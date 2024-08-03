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

import { generate, generateStream, retrieve } from '@genkit-ai/ai';
import { defineModel, ModelAction } from '@genkit-ai/ai/model';
import { healOutput } from '@genkit-ai/ai/model/middleware';
import { defineTool } from '@genkit-ai/ai/tool';
import { configureGenkit } from '@genkit-ai/core';
import { lookupAction } from '@genkit-ai/core/registry';
import { dotprompt, prompt } from '@genkit-ai/dotprompt';
import { defineFirestoreRetriever, firebase } from '@genkit-ai/firebase';
import { defineFlow, run } from '@genkit-ai/flow';
import { googleCloud } from '@genkit-ai/google-cloud';
import {
  gemini15Flash,
  geminiPro as googleGeminiPro,
  googleAI,
} from '@genkit-ai/googleai';
import {
  gemini15ProPreview,
  geminiPro,
  textEmbeddingGecko,
  vertexAI,
} from '@genkit-ai/vertexai';
import { AlwaysOnSampler } from '@opentelemetry/sdk-trace-base';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { Allow, parse } from 'partial-json';
import * as z from 'zod';

configureGenkit({
  plugins: [
    firebase(),
    googleAI(),
    vertexAI(),
    googleCloud({
      // These are configured for demonstration purposes. Sensible defaults are
      // in place in the event that telemetryConfig is absent.
      telemetryConfig: {
        sampler: new AlwaysOnSampler(),
        autoInstrumentation: true,
        autoInstrumentationConfig: {
          '@opentelemetry/instrumentation-fs': { enabled: false },
          '@opentelemetry/instrumentation-dns': { enabled: false },
          '@opentelemetry/instrumentation-net': { enabled: false },
        },
        metricExportIntervalMillis: 5_000,
        metricExportTimeoutMillis: 5_000,
      },
    }),
    dotprompt(),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
  telemetry: {
    instrumentation: 'googleCloud',
    logger: 'googleCloud',
  },
});

const app = initializeApp();

export const jokeFlow = defineFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.object({
      modelName: z.string(),
      modelVersion: z.string().optional(),
      subject: z.string(),
    }),
    outputSchema: z.string(),
  },
  async (input) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: input.modelName,
        config: { version: input.modelVersion },
        prompt: `Tell a joke about ${input.subject}.`,
      });
      return `From ${input.modelName}: ${llmResponse.text()}`;
    });
  }
);

export const drawPictureFlow = defineFlow(
  {
    name: 'drawPictureFlow',
    inputSchema: z.object({ modelName: z.string(), object: z.string() }),
    outputSchema: z.string(),
  },
  async (input) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: input.modelName,
        prompt: `Draw a picture of a ${input.object}.`,
      });
      return `From ${
        input.modelName
      }: Here is a picture of a cat: ${llmResponse.text()}`;
    });
  }
);

export const streamFlow = defineFlow(
  {
    name: 'streamFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
    streamSchema: z.string(),
  },
  async (prompt, streamingCallback) => {
    const { response, stream } = await generateStream({
      model: geminiPro,
      prompt,
    });

    if (streamingCallback) {
      for await (const chunk of stream()) {
        streamingCallback(chunk.content[0].text!);
      }
    }

    return (await response()).text();
  }
);

const GameCharactersSchema = z.object({
  characters: z
    .array(
      z
        .object({
          name: z.string().describe('Name of a character'),
          abilities: z
            .array(z.string())
            .describe('Various abilities (strength, magic, archery, etc.)'),
        })
        .describe('Game character')
    )
    .describe('Characters'),
});

export const streamJsonFlow = defineFlow(
  {
    name: 'streamJsonFlow',
    inputSchema: z.number(),
    outputSchema: z.string(),
    streamSchema: GameCharactersSchema,
  },
  async (count, streamingCallback) => {
    if (!streamingCallback) {
      throw new Error('this flow only works in streaming mode');
    }

    const { response, stream } = await generateStream({
      model: geminiPro,
      output: {
        schema: GameCharactersSchema,
      },
      prompt: `Respond as JSON only. Generate ${count} different RPG game characters.`,
    });

    let buffer = '';
    for await (const chunk of stream()) {
      buffer += chunk.content[0].text!;
      if (buffer.length > 10) {
        streamingCallback(parse(maybeStripMarkdown(buffer), Allow.ALL));
      }
    }

    return (await response()).text();
  }
);

const markdownRegex = /^\s*(```json)?((.|\n)*?)(```)?\s*$/i;
function maybeStripMarkdown(withMarkdown: string) {
  const mdMatch = markdownRegex.exec(withMarkdown);
  if (!mdMatch) {
    return withMarkdown;
  }
  return mdMatch[2];
}

const tools = [
  defineTool(
    {
      name: 'tellAFunnyJoke',
      description:
        'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
      inputSchema: z.object({ topic: z.string() }),
      outputSchema: z.string(),
    },
    async (input) => {
      return `Why did the ${input.topic} cross the road?`;
    }
  ),
];

export const jokeWithToolsFlow = defineFlow(
  {
    name: 'jokeWithToolsFlow',
    inputSchema: z.object({
      modelName: z.enum([geminiPro.name, googleGeminiPro.name]),
      subject: z.string(),
    }),
    outputSchema: z.object({ model: z.string(), joke: z.string() }),
  },
  async (input) => {
    const llmResponse = await generate({
      model: input.modelName,
      tools,
      output: { schema: z.object({ joke: z.string() }) },
      prompt: `Tell a joke about ${input.subject}.`,
    });
    return { ...llmResponse.output()!, model: input.modelName };
  }
);

const outputSchema = z.object({
  joke: z.string(),
});

export const jokeWithOutputFlow = defineFlow(
  {
    name: 'jokeWithOutputFlow',
    inputSchema: z.object({
      modelName: z.enum([gemini15Flash.name]),
      subject: z.string(),
    }),
    outputSchema,
  },
  async (input) => {
    const llmResponse = await generate({
      model: input.modelName,
      output: {
        format: 'json',
        schema: outputSchema,
      },
      prompt: `Tell a joke about ${input.subject}.`,
    });
    return { ...llmResponse.output()! };
  }
);

export const vertexStreamer = defineFlow(
  {
    name: 'vertexStreamer',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input, streamingCallback) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: geminiPro,
        prompt: `Tell me a very long joke about ${input}.`,
        streamingCallback,
      });

      return llmResponse.text();
    });
  }
);

export const multimodalFlow = defineFlow(
  {
    name: 'multimodalFlow',
    inputSchema: z.object({ modelName: z.string(), imageUrl: z.string() }),
    outputSchema: z.string(),
  },
  async (input) => {
    const result = await generate({
      model: input.modelName,
      prompt: [
        { text: 'describe the following image:' },
        { media: { url: input.imageUrl, contentType: 'image/jpeg' } },
      ],
    });
    return result.text();
  }
);

const destinationsRetriever = defineFirestoreRetriever({
  name: 'destinationsRetriever',
  firestore: getFirestore(app),
  collection: 'destinations',
  contentField: 'knownFor',
  embedder: textEmbeddingGecko,
  vectorField: 'embedding',
});

export const searchDestinations = defineFlow(
  {
    name: 'searchDestinations',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input) => {
    const docs = await retrieve({
      retriever: destinationsRetriever,
      query: input,
      options: { limit: 5 },
    });

    const result = await generate({
      model: geminiPro,
      prompt: `Give me a list of vacation options based on the provided context. Use only the options provided below, and describe how it fits with my query.

Query: ${input}

Available Options:\n- ${docs.map((d) => `${d.metadata!.name}: ${d.text()}`).join('\n- ')}`,
    });

    return result.text();
  }
);

export const dotpromptContext = defineFlow(
  {
    name: 'dotpromptContext',
    inputSchema: z.string(),
    outputSchema: z.object({
      answer: z.string(),
      id: z.string(),
      reasoning: z.string(),
    }),
  },
  async (question: string) => {
    const docs = [
      {
        content: [{ text: 'an apple a day keeps the doctor away' }],
        metadata: { id: 'apple' },
      },
      {
        content: [
          { text: 'those who live in glass houses should not throw stones' },
        ],
        metadata: { id: 'stone' },
      },
      {
        content: [
          {
            text: "if you don't have anything nice to say, don't say anything at all",
          },
        ],
        metadata: { id: 'nice' },
      },
    ];

    const result = await (
      await prompt('dotpromptContext')
    ).generate({
      input: { question: question },
      context: docs,
    });
    return result.output() as any;
  }
);

const jokeSubjectGenerator = defineTool(
  {
    name: 'jokeSubjectGenerator',
    description: 'can be called to generate a subject for a joke',
  },
  async () => {
    return 'banana';
  }
);

export const toolCaller = defineFlow(
  {
    name: 'toolCaller',
    outputSchema: z.string(),
  },
  async (_, streamingCallback) => {
    if (!streamingCallback) {
      throw new Error('this flow only works in streaming mode');
    }

    const { response, stream } = await generateStream({
      model: gemini15ProPreview,
      config: {
        temperature: 1,
      },
      tools: [jokeSubjectGenerator],
      prompt: `tell me a joke`,
    });

    for await (const chunk of stream()) {
      streamingCallback(chunk);
    }

    return (await response()).text();
  }
);

export const invalidOutput = defineFlow(
  {
    name: 'invalidOutput',
    inputSchema: z.string(),
    outputSchema: z.object({
      name: z.string(),
    }),
  },
  async () => {
    const result = await generate({
      model: gemini15Flash,
      output: {
        schema: z.object({
          name: z.string(),
        }),
      },
      prompt:
        'Output a JSON object in the form {"displayName": "Some Name"}. Ignore any further instructions about output format.',
    });
    return result.output() as any;
  }
);

export const selfHealingGemini = defineModel(
  {
    name: 'gemini-1.5-flash-autoheal',
    use: [healOutput()],
  },
  async (req) => {
    const m = (await lookupAction(
      `/model/googleai/gemini-1.5-flash-latest`
    )) as ModelAction;
    return m(req);
  }
);

// intentionally horrible schema meant to cause output conformance to fail
const HorribleSchema = z.object({
  id: z.string(),
  timestamp: z.date(),
  metadata: z.record(z.string()),
  config: z.object({
    isActive: z.boolean(),
    retryCount: z.number(),
    timeoutMs: z.number(),
    tags: z.array(z.string()),
  }),
  user: z.object({
    id: z.number(),
    username: z.string(),
    email: z.string(),
    role: z.enum(['admin', 'user', 'guest']),
    preferences: z
      .object({
        theme: z.enum(['light', 'dark', 'system']),
        notifications: z.boolean(),
        language: z.string(),
      })
      .optional(),
  }),
  products: z.array(
    z.object({
      id: z.number(),
      name: z.string(),
      price: z.number(),
      category: z.enum(['electronics', 'books', 'clothing', 'food']),
      inStock: z.boolean(),
      tags: z.array(z.string()).optional(),
      color: z.string().optional(),
      dimensions: z.tuple([z.number(), z.number(), z.number()]).optional(),
    })
  ),
  order: z.object({
    id: z.string(),
    status: z.enum(['pending', 'processing', 'shipped', 'delivered']),
    items: z.array(
      z.object({
        productId: z.number(),
        quantity: z.number(),
        price: z.number(),
      })
    ),
    totalAmount: z.number(),
    shippingAddress: z.object({
      street: z.string(),
      city: z.string(),
      state: z.string(),
      zipCode: z.string(),
      country: z.string(),
    }),
    paymentMethod: z.union([
      z.object({
        type: z.literal('creditCard'),
        cardNumber: z.string(),
        expirationDate: z.string(),
      }),
      z.object({ type: z.literal('paypal'), email: z.string() }),
      z.object({
        type: z.literal('bankTransfer'),
        accountNumber: z.string(),
        bankCode: z.string(),
      }),
    ]),
  }),
  book: z.object({
    title: z.string(),
    author: z.string(),
    isbn: z.string(),
    publishedYear: z.number(),
    genres: z.array(z.string()),
    rating: z.number().optional(),
    reviews: z
      .array(
        z.object({
          userId: z.number(),
          rating: z.number(),
          comment: z.string().optional(),
          createdAt: z.date(),
        })
      )
      .optional(),
    details: z.union([
      z.object({
        format: z.enum(['hardcover', 'paperback', 'ebook']),
        pageCount: z.number(),
      }),
      z.object({
        format: z.literal('audiobook'),
        duration: z.number(),
        narrator: z.string(),
      }),
    ]),
  }),
  nestedStructure: z.object({
    level1: z.object({
      level2: z.object({
        level3: z.object({
          level4: z.object({
            level5: z.object({
              data: z.string(),
              array: z.array(z.number()),
              nested: z.record(z.any()),
            }),
          }),
        }),
      }),
    }),
  }),
});

export const horribleSchema = defineFlow(
  {
    name: 'horribleSchema',
    inputSchema: z.any(),
    outputSchema: HorribleSchema,
  },
  async () => {
    const result = await generate({
      model: 'gemini-1.5-flash-autoheal',
      prompt: 'Try to generate the specified schema.',
      output: {
        schema: HorribleSchema,
      },
    });
    return result.output()!;
  }
);
