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

import { defineFirestoreRetriever } from '@genkit-ai/firebase';
import { enableGoogleCloudTelemetry } from '@genkit-ai/google-cloud';
import {
  gemini15Flash,
  googleAI,
  geminiPro as googleGeminiPro,
} from '@genkit-ai/googleai';
import {
  gemini15ProPreview,
  geminiPro,
  textEmbeddingGecko,
  vertexAI,
} from '@genkit-ai/vertexai';
import { GoogleAIFileManager } from '@google/generative-ai/server';
import { AlwaysOnSampler } from '@opentelemetry/sdk-trace-base';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { MessageSchema, dotprompt, genkit, prompt, run, z } from 'genkit';
import { runWithRegistry } from 'genkit/registry';
import { Allow, parse } from 'partial-json';

enableGoogleCloudTelemetry({
  // These are configured for demonstration purposes. Sensible defaults are
  // in place in the event that telemetryConfig is absent.

  // Forces telemetry export in 'dev'
  forceDevExport: true,
  sampler: new AlwaysOnSampler(),
  autoInstrumentation: true,
  autoInstrumentationConfig: {
    '@opentelemetry/instrumentation-fs': { enabled: false },
    '@opentelemetry/instrumentation-dns': { enabled: false },
    '@opentelemetry/instrumentation-net': { enabled: false },
  },
  metricExportIntervalMillis: 5_000,
  metricExportTimeoutMillis: 5_000,
});

const ai = genkit({
  plugins: [googleAI(), vertexAI(), dotprompt()],
});

const app = initializeApp();

export const jokeFlow = ai.defineFlow(
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
      const llmResponse = await ai.generate({
        model: input.modelName,
        config: { version: input.modelVersion },
        prompt: `Tell a joke about ${input.subject}.`,
      });
      return `From ${input.modelName}: ${llmResponse.text()}`;
    });
  }
);

export const drawPictureFlow = ai.defineFlow(
  {
    name: 'drawPictureFlow',
    inputSchema: z.object({ modelName: z.string(), object: z.string() }),
    outputSchema: z.string(),
  },
  async (input) => {
    return await run('call-llm', async () => {
      const llmResponse = await ai.generate({
        model: input.modelName,
        prompt: `Draw a picture of a ${input.object}.`,
      });
      return `From ${
        input.modelName
      }: Here is a picture of a cat: ${llmResponse.text()}`;
    });
  }
);

export const streamFlow = ai.defineStreamingFlow(
  {
    name: 'streamFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
    streamSchema: z.string(),
  },
  async (prompt, streamingCallback) => {
    const { response, stream } = await ai.generateStream({
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

export const streamJsonFlow = ai.defineStreamingFlow(
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

    const { response, stream } = await ai.generateStream({
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
  ai.defineTool(
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

export const jokeWithToolsFlow = ai.defineFlow(
  {
    name: 'jokeWithToolsFlow',
    inputSchema: z.object({
      modelName: z.enum([geminiPro.name, googleGeminiPro.name]),
      subject: z.string(),
    }),
    outputSchema: z.object({ model: z.string(), joke: z.string() }),
  },
  async (input) => {
    const llmResponse = await ai.generate({
      model: input.modelName as string,
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

export const jokeWithOutputFlow = ai.defineFlow(
  {
    name: 'jokeWithOutputFlow',
    inputSchema: z.object({
      modelName: z.enum([gemini15Flash.name]),
      subject: z.string(),
    }),
    outputSchema,
  },
  async (input) => {
    const llmResponse = await ai.generate({
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

export const vertexStreamer = ai.defineFlow(
  {
    name: 'vertexStreamer',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input, streamingCallback) => {
    return await run('call-llm', async () => {
      const llmResponse = await ai.generate({
        model: geminiPro,
        prompt: `Tell me a very long joke about ${input}.`,
        streamingCallback,
      });

      return llmResponse.text();
    });
  }
);

export const multimodalFlow = ai.defineFlow(
  {
    name: 'multimodalFlow',
    inputSchema: z.object({ modelName: z.string(), imageUrl: z.string() }),
    outputSchema: z.string(),
  },
  async (input) => {
    const result = await ai.generate({
      model: input.modelName,
      prompt: [
        { text: 'describe the following image:' },
        { media: { url: input.imageUrl, contentType: 'image/jpeg' } },
      ],
    });
    return result.text();
  }
);

const destinationsRetriever = runWithRegistry(ai.registry, () =>
  defineFirestoreRetriever({
    name: 'destinationsRetriever',
    firestore: getFirestore(app),
    collection: 'destinations',
    contentField: 'knownFor',
    embedder: textEmbeddingGecko,
    vectorField: 'embedding',
  })
);

export const searchDestinations = ai.defineFlow(
  {
    name: 'searchDestinations',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input) => {
    const docs = await ai.retrieve({
      retriever: destinationsRetriever,
      query: input,
      options: { limit: 5 },
    });

    const result = await ai.generate({
      model: geminiPro,
      prompt: `Give me a list of vacation options based on the provided context. Use only the options provided below, and describe how it fits with my query.

Query: ${input}

Available Options:\n- ${docs.map((d) => `${d.metadata!.name}: ${d.text()}`).join('\n- ')}`,
    });

    return result.text();
  }
);

export const dotpromptContext = ai.defineFlow(
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

const jokeSubjectGenerator = ai.defineTool(
  {
    name: 'jokeSubjectGenerator',
    description: 'can be called to generate a subject for a joke',
  },
  async () => {
    return 'banana';
  }
);

export const toolCaller = ai.defineStreamingFlow(
  {
    name: 'toolCaller',
    outputSchema: z.string(),
    streamSchema: z.any(),
  },
  async (_, streamingCallback) => {
    if (!streamingCallback) {
      throw new Error('this flow only works in streaming mode');
    }

    const { response, stream } = await ai.generateStream({
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

export const invalidOutput = ai.defineFlow(
  {
    name: 'invalidOutput',
    inputSchema: z.string(),
    outputSchema: z.object({
      name: z.string(),
    }),
  },
  async () => {
    const result = await ai.generate({
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

const fileManager = new GoogleAIFileManager(
  process.env.GOOGLE_GENAI_API_KEY || process.env.GOOGLE_API_KEY!
);
export const fileApi = ai.defineFlow(
  {
    name: 'fileApi',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async () => {
    const uploadResult = await fileManager.uploadFile(
      '../menu/data/menu.jpeg',
      {
        mimeType: 'image/jpeg',
        displayName: 'Restaurant Menu',
      }
    );
    console.log(uploadResult.file);

    const result = await ai.generate({
      model: gemini15Flash,
      prompt: [
        { text: 'Describe this image:' },
        {
          media: {
            contentType: uploadResult.file.mimeType,
            url: uploadResult.file.uri,
          },
        },
      ],
    });

    return result.text();
  }
);

export const testTools = [
  // test a tool with no input / output schema
  ai.defineTool(
    { name: 'getColor', description: 'gets a random color' },
    async () => {
      const colors = [
        'red',
        'orange',
        'yellow',
        'blue',
        'green',
        'indigo',
        'violet',
      ];
      return colors[Math.floor(Math.random() * colors.length)];
    }
  ),
];

export const toolTester = ai.defineFlow(
  {
    name: 'toolTester',
    inputSchema: z.string(),
    outputSchema: z.array(MessageSchema),
  },
  async (query) => {
    const result = await ai.generate({
      model: gemini15Flash,
      prompt: query,
      tools: testTools,
    });
    return result.toHistory();
  }
);
