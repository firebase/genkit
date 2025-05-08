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

import { genkitEval, GenkitMetric } from '@genkit-ai/evaluator';
import { defineFirestoreRetriever } from '@genkit-ai/firebase';
import { enableGoogleCloudTelemetry } from '@genkit-ai/google-cloud';
import {
  gemini15Flash,
  gemini20Flash,
  gemini20FlashExp,
  googleAI,
  gemini10Pro as googleGemini10Pro,
} from '@genkit-ai/googleai';
import {
  textEmbedding004,
  vertexAI,
  gemini15Flash as vertexGemini15Flash,
} from '@genkit-ai/vertexai';
import { GoogleAIFileManager } from '@google/generative-ai/server';
import { AlwaysOnSampler } from '@opentelemetry/sdk-trace-base';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { GenerateResponseData, genkit, MessageSchema, z } from 'genkit';
import { logger } from 'genkit/logging';
import { ModelMiddleware, simulateConstrainedGeneration } from 'genkit/model';
import { PluginProvider } from 'genkit/plugin';
import { Allow, parse } from 'partial-json';

logger.setLogLevel('debug');

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
  plugins: [
    googleAI({ experimental_debugTraces: true }),
    vertexAI({ location: 'us-central1', experimental_debugTraces: true }),
    genkitEval({
      metrics: [
        GenkitMetric.DEEP_EQUAL,
        GenkitMetric.REGEX,
        GenkitMetric.JSONATA,
      ],
    }),
  ],
});

const math: PluginProvider = {
  name: 'math',
  initializer: async () => {
    ai.defineTool(
      {
        name: 'math/add',
        description: 'add two numbers',
        inputSchema: z.object({ a: z.number(), b: z.number() }),
        outputSchema: z.number(),
      },
      async ({ a, b }) => a + b
    );

    ai.defineTool(
      {
        name: 'math/subtract',
        description: 'subtract two numbers',
        inputSchema: z.object({ a: z.number(), b: z.number() }),
        outputSchema: z.number(),
      },
      async ({ a, b }) => a - b
    );
  },
};
ai.registry.registerPluginProvider('math', math);

const app = initializeApp();

export const jokeFlow = ai.defineFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.object({
      modelName: z.string().default('vertexai/gemini-2.5-pro-exp-03-25'),
      modelVersion: z.string().optional().default('gemini-2.5-pro-exp-03-25'),
      subject: z.string().default('bananas'),
    }),
    outputSchema: z.string(),
  },
  async (input) => {
    return await ai.run('call-llm', async () => {
      const llmResponse = await ai.generate({
        model: input.modelName,
        config: { version: input.modelVersion },
        prompt: `Tell a joke about ${input.subject}.`,
      });
      return `From ${input.modelName}: ${llmResponse.text}`;
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
    return await ai.run('call-llm', async () => {
      const llmResponse = await ai.generate({
        model: input.modelName,
        prompt: `Draw a picture of a ${input.object}.`,
      });
      return `From ${input.modelName}: Here is a picture of a cat: ${llmResponse.text}`;
    });
  }
);

export const streamFlowVertex = ai.defineFlow(
  {
    name: 'streamFlowVertex',
    inputSchema: z.string(),
    outputSchema: z.string(),
    streamSchema: z.string(),
  },
  async (prompt, { sendChunk }) => {
    const { response, stream } = ai.generateStream({
      model: vertexAI.model('gemini-2.0-flash-001', { temperature: 0.77 }),
      prompt,
    });

    for await (const chunk of stream) {
      sendChunk(chunk.content[0].text!);
    }

    return (await response).text;
  }
);
export const streamFlowGemini = ai.defineFlow(
  {
    name: 'streamFlowGemini',
    inputSchema: z.string(),
    outputSchema: z.string(),
    streamSchema: z.string(),
  },
  async (prompt, { sendChunk }) => {
    const { response, stream } = ai.generateStream({
      model: googleAI.model('gemini-2.0-flash-001', { temperature: 0.77 }),
      prompt,
    });

    for await (const chunk of stream) {
      sendChunk(chunk.content[0].text!);
    }

    return (await response).text;
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

export const streamJsonFlow = ai.defineFlow(
  {
    name: 'streamJsonFlow',
    inputSchema: z.number(),
    outputSchema: z.string(),
    streamSchema: GameCharactersSchema,
  },
  async (count, { sendChunk }) => {
    const { response, stream } = ai.generateStream({
      model: gemini15Flash,
      output: {
        schema: GameCharactersSchema,
      },
      prompt: `Respond as JSON only. Generate ${count} different RPG game characters.`,
    });

    let buffer = '';
    for await (const chunk of stream) {
      buffer += chunk.content[0].text!;
      if (buffer.length > 10) {
        sendChunk(parse(maybeStripMarkdown(buffer), Allow.ALL));
      }
    }

    return (await response).text;
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
      modelName: z.enum([gemini15Flash.name, googleGemini10Pro.name]),
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
    return { ...llmResponse.output!, model: input.modelName };
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
  async (input, { sendChunk }) => {
    const llmResponse = await ai.generate({
      model: input.modelName,
      output: {
        format: 'json',
        schema: outputSchema,
      },
      prompt: `Tell a long joke about ${input.subject}.`,
      use: [simulateConstrainedGeneration()],
      onChunk: (c) => sendChunk(c.output),
    });
    return { ...llmResponse.output! };
  }
);

export const vertexStreamer = ai.defineFlow(
  {
    name: 'vertexStreamer',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input, { sendChunk }) => {
    return await ai.run('call-llm', async () => {
      const llmResponse = await ai.generate({
        model: gemini15Flash,
        prompt: `Tell me a very long joke about ${input}.`,
        onChunk: (c) => sendChunk(c.text),
      });

      return llmResponse.text;
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
    return result.text;
  }
);

const destinationsRetriever = defineFirestoreRetriever(ai, {
  name: 'destinationsRetriever',
  firestore: getFirestore(app),
  collection: 'destinations',
  contentField: 'knownFor',
  embedder: textEmbedding004,
  vectorField: 'embedding',
});

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
      model: gemini15Flash,
      prompt: `Give me a list of vacation options based on the provided context. Use only the options provided below, and describe how it fits with my query.

Query: ${input}

Available Options:\n- ${docs.map((d) => `${d.metadata!.name}: ${d.text}`).join('\n- ')}`,
    });

    return result.text;
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

    const result = await ai.prompt('dotpromptContext')(
      { question: question },
      {
        docs,
      }
    );
    return result.output as any;
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

const gablorkenTool = ai.defineTool(
  {
    name: 'gablorkenTool',
    inputSchema: z.object({
      value: z
        .number()
        .describe(
          'always add 1 to the value (it is 1 based, but upstream it is zero based)'
        ),
    }),
    description: 'can be used to calculate gablorken value',
  },
  async (input) => {
    return input.value * 3 - 4;
  }
);

const characterGenerator = ai.defineTool(
  {
    name: 'characterGenerator',
    inputSchema: z.object({
      age: z.number().describe('must be between 23 and 27'),
      type: z.enum(['archer', 'banana']),
      name: z.string().describe('can only be Bob or John'),
      surname: z.string(),
    }),
    description:
      'can be used to generate a character. Seed it with some input.',
  },
  async (input) => {
    return input;
  }
);

export const toolCaller = ai.defineFlow(
  {
    name: 'toolCaller',
    outputSchema: z.string(),
    streamSchema: z.any(),
  },
  async (_, { sendChunk }) => {
    const { response, stream } = ai.generateStream({
      model: gemini15Flash,
      config: {
        temperature: 1,
      },
      tools: [jokeSubjectGenerator],
      prompt: `tell me a joke`,
    });

    for await (const chunk of stream) {
      sendChunk(chunk);
    }

    return (await response).text;
  }
);

export const dynamicToolCaller = ai.defineFlow(
  {
    name: 'dynamicToolCaller',
    inputSchema: z.number().default(5),
    outputSchema: z.string(),
    streamSchema: z.any(),
  },
  async (input, { sendChunk }) => {
    const dynamicGablorkenTool = ai.dynamicTool(
      {
        name: 'dynamicGablorkenTool',
        inputSchema: z.object({
          value: z
            .number()
            .describe(
              'always add 1 to the value (it is 1 based, but upstream it is zero based)'
            ),
        }),
        description: 'can be used to calculate gablorken value',
      },
      async (input) => {
        return input.value * 3 - 4;
      }
    );

    const { response, stream } = ai.generateStream({
      model: googleAI.model('gemini-2.0-flash'),
      config: {
        temperature: 1,
      },
      tools: [dynamicGablorkenTool],
      prompt: `what is a gablorken of ${input}`,
    });

    for await (const chunk of stream) {
      sendChunk(chunk);
    }

    return (await response).text;
  }
);

const exitTool = ai.defineTool(
  {
    name: 'exitTool',
    inputSchema: z.object({
      answer: z.number(),
    }),
    description: 'call this tool when you have the final answer',
  },
  async (input, { interrupt }) => {
    interrupt();
  }
);

export const forcedToolCaller = ai.defineFlow(
  {
    name: 'forcedToolCaller',
    inputSchema: z.number(),
    streamSchema: z.any(),
  },
  async (input, { sendChunk }) => {
    const { response, stream } = ai.generateStream({
      model: vertexGemini15Flash,
      config: {
        temperature: 1,
      },
      tools: [gablorkenTool, exitTool],
      toolChoice: 'required',
      prompt: `what is a gablorken of ${input}`,
    });

    for await (const chunk of stream) {
      sendChunk(chunk);
    }

    return await response;
  }
);

export const toolCallerCharacterGenerator = ai.defineFlow(
  {
    name: 'toolCallerCharacterGenerator',
    inputSchema: z.number(),
    streamSchema: z.any(),
  },
  async (input, { sendChunk }) => {
    const { response, stream } = ai.generateStream({
      model: vertexGemini15Flash,
      config: {
        temperature: 1,
      },
      tools: [characterGenerator, exitTool],
      toolChoice: 'required',
      prompt: `generate an archer character`,
    });

    for await (const chunk of stream) {
      sendChunk(chunk);
    }

    return await response;
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
    return result.output as any;
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

    return result.text;
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
    return result.messages;
  }
);

export const arrayStreamTester = ai.defineFlow(
  {
    name: 'arrayStreamTester',
    inputSchema: z.string().nullish(),
    outputSchema: z.any(),
    streamSchema: z.any(),
  },
  async (input, { sendChunk }) => {
    try {
      const { stream, response } = ai.generateStream({
        model: gemini15Flash,
        config: {
          safetySettings: [
            {
              category: 'HARM_CATEGORY_HATE_SPEECH',
              threshold: 'BLOCK_NONE',
            },
            {
              category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
              threshold: 'BLOCK_NONE',
            },
            {
              category: 'HARM_CATEGORY_HARASSMENT',
              threshold: 'BLOCK_NONE',
            },
            {
              category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
              threshold: 'BLOCK_NONE',
            },
          ],
        },
        prompt: `Generate a list of 20 characters from ${input || 'Futurama'}`,
        output: {
          format: 'array',
          schema: z.array(
            z.object({
              name: z.string(),
              description: z.string(),
              friends: z.array(z.string()),
              enemies: z.array(z.string()),
            })
          ),
        },
      });

      for await (const { output, text } of stream) {
        sendChunk({ text, output });
      }

      const result = await response;
      console.log(result.parser);
      return result.output;
    } catch (e: any) {
      return 'Error: ' + e.message;
    }
  }
);

ai.defineFlow(
  {
    name: 'math',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (query, { sendChunk }) => {
    const { text } = await ai.generate({
      model: gemini15Flash,
      prompt: query,
      tools: ['math/add', 'math/subtract'],
      onChunk: sendChunk,
    });
    return text;
  }
);

ai.defineModel(
  {
    name: 'hiModel',
  },
  async () => {
    return {
      finishReason: 'stop',
      message: { role: 'model', content: [{ text: 'hi' }] },
    };
  }
);

const blockingMiddleware: ModelMiddleware = async (req, next) => {
  return {
    finishReason: 'blocked',
    finishMessage: `Model input violated policies: further processing blocked.`,
  } as GenerateResponseData;
};

ai.defineFlow('blockingMiddleware', async () => {
  const { text } = await ai.generate({
    prompt: 'hi',
    model: 'hiModel',
    use: [blockingMiddleware],
  });
  return text;
});

ai.defineFlow('formatJson', async (input, { sendChunk }) => {
  const { output, text } = await ai.generate({
    model: gemini15Flash,
    prompt: `generate an RPG game character of type ${input || 'archer'}`,
    output: {
      constrained: true,
      instructions: true,
      schema: z
        .object({
          name: z.string(),
          weapon: z.string(),
        })
        .strict(),
    },
    onChunk: (c) => sendChunk(c.output),
  });
  return { output, text };
});

ai.defineFlow('formatJsonManualSchema', async (input, { sendChunk }) => {
  const { output, text } = await ai.generate({
    model: gemini15Flash,
    prompt: `generate one RPG game character of type ${input || 'archer'} and generated JSON must match this interface

    \`\`\`typescript
    interface Character {
      name: string;
      weapon: string;
    }
    \`\`\`
    `,
    output: {
      constrained: true,
      instructions: false,
      schema: z
        .object({
          name: z.string(),
          weapon: z.string(),
        })
        .strict(),
    },
    onChunk: (c) => sendChunk(c.output),
  });
  return { output, text };
});

ai.defineFlow('testArray', async (input, { sendChunk }) => {
  const { output } = await ai.generate({
    prompt: `10 different weapons for ${input}`,
    output: {
      format: 'array',
      schema: z.array(z.string()),
    },
    onChunk: (c) => sendChunk(c.output),
  });
  return output;
});

ai.defineFlow('formatEnum', async (input, { sendChunk }) => {
  const { output } = await ai.generate({
    prompt: `classify the denger level of sky diving`,
    output: {
      format: 'enum',
      schema: z.enum(['safe', 'dangerous', 'medium']),
    },
    onChunk: (c) => sendChunk(c.output),
  });
  return output;
});

ai.defineFlow('formatJsonl', async (input, { sendChunk }) => {
  const { output } = await ai.generate({
    prompt: `generate 5 randon persons`,
    output: {
      format: 'jsonl',
      schema: z.array(
        z.object({ name: z.string(), surname: z.string() }).strict()
      ),
    },
    onChunk: (c) => sendChunk(c.output),
  });
  return output;
});

ai.defineFlow('simpleDataExtractor', async (input) => {
  const { output } = await ai.generate({
    model: gemini15Flash,
    prompt: `extract data from:\n\n${input}`,
    output: {
      schema: z.object({
        name: z.string(),
        age: z.number(),
      }),
    },
  });
  return output;
});

ai.defineFlow('echo', async (input) => {
  return input;
});

ai.defineFlow(
  {
    name: 'youtube',
    inputSchema: z.object({
      url: z.string(),
      prompt: z.string(),
      model: z.string().optional(),
    }),
  },
  async ({ url, prompt, model }) => {
    const { text } = await ai.generate({
      model: model || 'googleai/gemini-2.0-flash',
      prompt: [{ text: prompt }, { media: { url, contentType: 'video/mp4' } }],
    });
    return text;
  }
);

ai.defineFlow(
  {
    name: 'geminiImages',
    inputSchema: z.string().optional(),
  },
  async (setting) => {
    const { message } = await ai.generate({
      model: gemini20FlashExp,
      prompt: `Generate a choose your own adventure intro${setting ? ` in ${setting}` : ''}, then generate a first-person image as if I'm in the story.`,
      config: {
        responseModalities: ['TEXT', 'IMAGE'],
      },
    });

    return message?.content;
  }
);

ai.defineFlow('geminiEnum', async (thing) => {
  const { output } = await ai.generate({
    model: gemini20Flash,
    prompt: `What type of thing is ${thing || 'a banana'}?`,
    output: {
      schema: z.object({
        type: z.enum(['FRUIT', 'VEGETABLE', 'MINERAL']),
      }),
    },
  });

  return output;
});

ai.defineFlow('embedders-tester', async () => {
  console.log(
    await ai.embed({
      content: 'hello world',
      embedder: googleAI.embedder('text-embedding-004'),
    })
  );
  console.log(
    await ai.embed({
      content: 'hello world',
      embedder: vertexAI.embedder('text-embedding-004'),
    })
  );
});
