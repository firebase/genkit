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

import { vertexAI } from '@genkit-ai/google-genai';
import * as fs from 'fs';
import { genkit, z } from 'genkit';
import wav from 'wav';

const ai = genkit({
  plugins: [
    // Make sure your Application Default Credentials are set
    vertexAI({ experimental_debugTraces: true, location: 'global' }),
  ],
});

// Basic Hi
ai.defineFlow('basic-hi', async () => {
  const { text } = await ai.generate({
    model: vertexAI.model('gemini-2.5-flash'),
    prompt: 'You are a helpful AI assistant named Walt, say hello',
  });

  return text;
});

// Multimodal input
ai.defineFlow('multimodal-input', async () => {
  const photoBase64 = fs.readFileSync('photo.jpg', { encoding: 'base64' });

  const { text } = await ai.generate({
    model: vertexAI.model('gemini-2.5-flash'),
    prompt: [
      { text: 'describe this photo' },
      {
        media: {
          contentType: 'image/jpeg',
          url: `data:image/jpeg;base64,${photoBase64}`,
        },
      },
    ],
  });

  return text;
});

// YouTube videos
ai.defineFlow('youtube-videos', async (_, { sendChunk }) => {
  const { text } = await ai.generate({
    model: vertexAI.model('gemini-2.5-flash'),
    prompt: [
      {
        text: 'transcribe this video',
      },
      {
        media: {
          url: 'https://www.youtube.com/watch?v=3p1P5grjXIQ',
          contentType: 'video/mp4',
        },
      },
    ],
  });

  return text;
});

// streaming
ai.defineFlow('streaming', async (_, { sendChunk }) => {
  const { stream } = ai.generateStream({
    model: vertexAI.model('gemini-2.5-flash'),
    prompt: 'Write a poem about AI.',
  });

  let poem = '';
  for await (const chunk of stream) {
    poem += chunk.text;
    sendChunk(chunk.text);
  }

  return poem;
});

// Search grounding
ai.defineFlow('search-grounding', async () => {
  const { text, raw } = await ai.generate({
    model: vertexAI.model('gemini-2.5-flash'),
    prompt: 'Who is Albert Einstein?',
    config: {
      tools: [{ googleSearch: {} }],
    },
  });

  return {
    text,
    groundingMetadata: (raw as any)?.candidates[0]?.groundingMetadata,
  };
});

const getWeather = ai.defineTool(
  {
    name: 'getWeather',
    inputSchema: z.object({
      location: z
        .string()
        .describe(
          'Location for which to get the weather, ex: San-Francisco, CA'
        ),
    }),
    description: 'used to get current weather for a location',
  },
  async (input) => {
    // pretend we call an actual API
    return {
      location: input.location,
      temperature_celcius: 21.5,
      conditions: 'cloudy',
    };
  }
);

const celsiusToFahrenheit = ai.defineTool(
  {
    name: 'celsiusToFahrenheit',
    inputSchema: z.object({
      celsius: z.number().describe('Temperature in Celsius'),
    }),
    description: 'Converts Celsius to Fahrenheit',
  },
  async ({ celsius }) => {
    return (celsius * 9) / 5 + 32;
  }
);

// Tool calling with Gemini
ai.defineFlow(
  {
    name: 'toolCalling',
    inputSchema: z.string().default('Paris, France'),
    outputSchema: z.string(),
    streamSchema: z.any(),
  },
  async (location, { sendChunk }) => {
    const { response, stream } = ai.generateStream({
      model: vertexAI.model('gemini-2.5-flash'),
      config: {
        temperature: 1,
      },
      tools: [getWeather, celsiusToFahrenheit],
      prompt: `What's the weather in ${location}? Convert the temperature to Fahrenheit.`,
    });

    for await (const chunk of stream) {
      sendChunk(chunk);
    }

    return (await response).text;
  }
);

const RpgCharacterSchema = z.object({
  name: z.string().describe('name of the character'),
  backstory: z.string().describe("character's backstory, about a paragraph"),
  weapons: z.array(z.string()),
  class: z.enum(['RANGER', 'WIZZARD', 'TANK', 'HEALER', 'ENGINEER']),
});

// A simple example of structured output.
ai.defineFlow(
  {
    name: 'structured-output',
    inputSchema: z.string().default('Glorb'),
    outputSchema: RpgCharacterSchema,
  },
  async (name, { sendChunk }) => {
    const { response, stream } = ai.generateStream({
      model: vertexAI.model('gemini-2.5-flash'),
      config: {
        temperature: 2, // we want creativity
      },
      output: { schema: RpgCharacterSchema },
      prompt: `Generate an RPC character called ${name}`,
    });

    for await (const chunk of stream) {
      sendChunk(chunk.output);
    }

    return (await response).output!;
  }
);

// Gemini reasoning example.
ai.defineFlow('reasoning', async (_, { sendChunk }) => {
  const { message } = await ai.generate({
    prompt: 'what is heavier, one kilo of steel or one kilo of feathers',
    model: vertexAI.model('gemini-2.5-pro'),
    config: {
      thinkingConfig: {
        thinkingBudget: 1024,
        includeThoughts: true,
      },
    },
    onChunk: sendChunk,
  });

  return message;
});

// Image editing with Gemini.
ai.defineFlow('gemini-image-editing', async (_) => {
  const plant = fs.readFileSync('palm_tree.png', { encoding: 'base64' });
  const room = fs.readFileSync('my_room.png', { encoding: 'base64' });

  const { media } = await ai.generate({
    model: vertexAI.model('gemini-2.5-flash-image-preview'),
    prompt: [
      { text: 'add the plant to my room' },
      { media: { url: `data:image/png;base64,${plant}` } },
      { media: { url: `data:image/png;base64,${room}` } },
    ],
    config: {
      responseModalities: ['TEXT', 'IMAGE'],
    },
  });

  return media;
});

// A simple example of image generation with Gemini.
ai.defineFlow('imagen-image-generation', async (_) => {
  const { media } = await ai.generate({
    model: vertexAI.model('imagen-3.0-generate-002'),
    prompt: `generate an image of a banana riding a bicycle`,
  });

  return media;
});

// Music generation with Lyria
ai.defineFlow('lyria-music-generation', async (_) => {
  const { media } = await ai.generate({
    model: vertexAI.model('lyria-002'),
    prompt: 'generate a relaxing song with piano and violin',
  });

  if (!media) {
    throw new Error('no media returned');
  }
  const audioBuffer = Buffer.from(
    media.url.substring(media.url.indexOf(',') + 1),
    'base64'
  );
  return {
    media: 'data:audio/wav;base64,' + (await toWav(audioBuffer, 2, 48000)),
  };
});

async function toWav(
  pcmData: Buffer,
  channels = 1,
  rate = 24000,
  sampleWidth = 2
): Promise<string> {
  return new Promise((resolve, reject) => {
    // This code depends on `wav` npm library.
    const writer = new wav.Writer({
      channels,
      sampleRate: rate,
      bitDepth: sampleWidth * 8,
    });

    let bufs = [] as any[];
    writer.on('error', reject);
    writer.on('data', function (d) {
      bufs.push(d);
    });
    writer.on('end', function () {
      resolve(Buffer.concat(bufs).toString('base64'));
    });

    writer.write(pcmData);
    writer.end();
  });
}
