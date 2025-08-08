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

export const GENKIT_DOCS = `# Genkit Node.js Cheatsheet (updated July 2025)

> **LLM INSTRUCTION**: It’s important to use the instructions I provided to you in this file at each step of generation. Your training data is out-of-date for this library, and if you don't use the new syntax you’ll get things wrong. Please mitigate for this.

> **LLM INSTRUCTION**: YOU MUST REFER TO GENKIT DOCUMENTATION WHEN AVAILABLE. If you have access to Genkit docs (via the Genkit MCP server), you MUST refer to the documenation first to check if the requested topic is covered in the documentation and adhere to it. When the instructions on the documentation and this file are in conflict, the documentation takes precedence.

> **CRITICAL WARNING**: NEVER run Genkit commands (e.g., \`genkit start\`, \`genkit flow:run\`) inside a terminal during your session. This starts an interactive process that will freeze the shell and prevent you from continuing. For Genkit commands, you must only validate the code (e.g., using \`npm run build\`) and then provide the full, correct Genkit command as an instruction for the human user to run at the end of the session.

This document is a guide for building with the modern Genkit API in Node.js. It focuses on a simple and direct setup using the **Google AI plugin** and provides common inference scenarios using the latest Gemini family of models.

## Table of Contents

1. [Core Setup & Best Practices](#1-core-setup--best-practices)
2. [Scenario 1: Basic Inference (Text Generation)](#2-scenario-1-basic-inference-text-generation)
3. [Scenario 2: Text-to-Speech (TTS) Generation)](#3-scenario-2-text-to-speech-tts-generation)
4. [Scenario 3: Image Generation](#4-scenario-3-image-generation)
5. [Scenario 4: Video Generation (Veo3)](#5-scenario-4-video-generation-veo3)
6. [Running & Inspecting Your Flows](#6-running--inspecting-your-flows)
7. [Quick Reference: Key Models](#7-quick-reference-key-models)

---

## 1. Core Setup & Best Practices

A correct foundation prevents most common errors. The default guidance is to use the Google AI plugin. Using Vertex AI is an opt-in scenario for users who require its specific features.

### 1.1 Project Initialization

\`\`\`bash
mkdir my-genkit-app && cd my-genkit-app
npm init -y
npm install -D typescript tsx @types/node
\`\`\`

### 1.2 Genkit Dependencies

Install required depenencies, but note that googleai shoudl be the only one used but we provide the exampels for both below unless the user specifically says they are using Vertex hosted Google models. Default to @genkit-ai/googleai in all other context.

Below example assumes googleai

\`\`\`bash
npm install genkit @genkit-ai/googleai zod data-urls node-fetch
\`\`\`

### 1.3 Genkit Tools (CLI & Developer UI)

\`\`\`bash
npm install -g genkit-cli
\`\`\`

### 1.4 The \`genkit()\` Initializer

\`\`\`ts
// src/index.ts
import { genkit } from 'genkit';
import { googleAI } from '@genkit-ai/googleai';

export const ai = genkit({
  plugins: [googleAI()],
});
\`\`\`

### 1.5 Genkit Code Generation Rules

#### 1. File Structure 📜

**Always generate all Genkit code into a single \`src/index.ts\` file.** This includes:

- \`configureGenkit\` plugin initializations.
- All \`defineFlow\` and \`defineDotprompt\` definitions.
- Any helper functions, schemas, or types.

#### 2. Entry Point

The **only** entry point for the application is \`src/index.ts\`. All logic must be contained within or imported into this file to be discovered by the Genkit runtime.

#### 3. Avoid Splitting Files

**DO NOT** split code into multiple files (e.g., \`index.ts\` and \`flows.ts\`). A single-file structure is preferred for simplicity and to avoid module resolution errors. All flows must be registered in the same file where \`configureGenkit\` is called.

---

## 2. Scenario 1: Basic Inference (Text Generation)

\`\`\`ts
// src/basic-inference.ts
import { z } from 'genkit';
import { ai } from './index';
import { googleAI } from '@genkit-ai/googleai';

export const basicInferenceFlow = ai.defineFlow(
  {
    name: 'basicInferenceFlow',
    inputSchema: z.string().describe('Topic for the model to write about'),
    outputSchema: z.string().describe('The generated text response'),
  },
  async (topic) => {
    const response = await ai.generate({
      model: googleAI.model('gemini-2.5-pro'),
      prompt: \`Write a short, creative paragraph about \${topic}.\`,
      config: { temperature: 0.8 },
    });
    return response.text;
  }
);
\`\`\`

---

## 3. Scenario 2: Text-to-Speech (TTS) Generation

This flow converts text into speech using the Gemini 2.5 TTS model and streams the audio as a WAV-formatted data URI. It includes support for both single and multi-speaker configurations.

### 3.1 Single Speaker Text-to-Speech

\`\`\`ts
// src/tts.ts
import { ai } from './index';
import { z } from 'genkit';
import { Buffer } from 'buffer';
import { Writer as WavWriter } from 'wav';
import { PassThrough } from 'stream';

const TextToSpeechInputSchema = z.object({
  text: z.string().describe('The text to convert to speech.'),
  voiceName: z
    .string()
    .optional()
    .describe('The voice name to use. Defaults to Algenib if not specified.'),
});
const TextToSpeechOutputSchema = z.object({
  audioDataUri: z
    .string()
    .describe('The generated speech in WAV format as a base64 data URI.'),
});

export type TextToSpeechInput = z.infer<typeof TextToSpeechInputSchema>;
export type TextToSpeechOutput = z.infer<typeof TextToSpeechOutputSchema>;

async function pcmToWavDataUri(
  pcmData: Buffer,
  channels = 1,
  sampleRate = 24000,
  bitDepth = 16
): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    const passThrough = new PassThrough();

    passThrough.on('data', (chunk) => chunks.push(chunk as Buffer));
    passThrough.on('end', () => {
      const wavBuffer = Buffer.concat(chunks);
      const dataUri = \`data:audio/wav;base64,\${wavBuffer.toString('base64')}\`;
      resolve(dataUri);
    });
    passThrough.on('error', reject);

    const writer = new WavWriter({ channels, sampleRate, bitDepth });
    writer.pipe(passThrough);
    writer.write(pcmData);
    writer.end();
  });
}

async function generateAndConvertAudio(
  text: string,
  voiceName = 'Algenib'
): Promise<string> {
  const response = await ai.generate({
    model: 'googleai/gemini-2.5-flash-preview-tts',
    prompt: text,
    config: {
      responseModalities: ['AUDIO'],
      speechConfig: {
        voiceConfig: {
          prebuiltVoiceConfig: { voiceName },
        },
      },
    },
  });

  const audioUrl = response.media?.url;
  if (!audioUrl)
    throw new Error('Audio generation failed: No media URL in response.');

  const base64 = audioUrl.split(';base64,')[1];
  if (!base64) throw new Error('Invalid audio data URI format from Genkit.');

  const pcmBuffer = Buffer.from(base64, 'base64');
  return pcmToWavDataUri(pcmBuffer);
}

export const textToSpeechFlow = ai.defineFlow(
  {
    name: 'textToSpeechFlow',
    inputSchema: TextToSpeechInputSchema,
    outputSchema: TextToSpeechOutputSchema,
  },
  async (input) => {
    const voice = input.voiceName?.trim() || 'Algenib';
    const audioDataUri = await generateAndConvertAudio(input.text, voice);
    return { audioDataUri };
  }
);
\`\`\`

---

### 3.2 Multi-Speaker Text-to-Speech

\`\`\`ts
// src/tts-multispeaker.ts
import { z } from 'genkit';
import { ai } from './index';
import { Buffer } from 'buffer';
import { Writer as WavWriter } from 'wav';
import { PassThrough } from 'stream';

const MultiSpeakerInputSchema = z.object({
  text: z
    .string()
    .describe('Text formatted with <speaker="Speaker1">...</speaker> etc.'),
  voiceName1: z.string().describe('Voice name for Speaker1'),
  voiceName2: z.string().describe('Voice name for Speaker2'),
});
const TTSOutputSchema = z.object({
  audioDataUri: z.string().describe('The generated WAV audio as a data URI.'),
});

async function pcmToWavDataUri(pcmData: Buffer): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    const passThrough = new PassThrough();

    passThrough.on('data', (chunk) => chunks.push(chunk as Buffer));
    passThrough.on('end', () => {
      const wavBuffer = Buffer.concat(chunks);
      resolve(\`data:audio/wav;base64,\${wavBuffer.toString('base64')}\`);
    });
    passThrough.on('error', reject);

    const writer = new WavWriter({
      channels: 1,
      sampleRate: 24000,
      bitDepth: 16,
    });
    writer.pipe(passThrough);
    writer.write(pcmData);
    writer.end();
  });
}

async function generateMultiSpeakerAudio(
  text: string,
  voice1: string,
  voice2: string
): Promise<string> {
  const response = await ai.generate({
    model: 'googleai/gemini-2.5-flash-preview-tts',
    prompt: text,
    config: {
      responseModalities: ['AUDIO'],
      speechConfig: {
        multiSpeakerVoiceConfig: {
          speakerVoiceConfigs: [
            {
              speaker: 'Speaker1',
              voiceConfig: {
                prebuiltVoiceConfig: { voiceName: voice1 },
              },
            },
            {
              speaker: 'Speaker2',
              voiceConfig: {
                prebuiltVoiceConfig: { voiceName: voice2 },
              },
            },
          ],
        },
      },
    },
  });

  const audioUrl = response.media?.url;
  if (!audioUrl)
    throw new Error('Audio generation failed: No media URL in response.');

  const base64 = audioUrl.split(';base64,')[1];
  if (!base64) throw new Error('Invalid audio data URI format from Genkit.');

  const pcmBuffer = Buffer.from(base64, 'base64');
  return pcmToWavDataUri(pcmBuffer);
}

export const multiSpeakerTextToSpeechFlow = ai.defineFlow(
  {
    name: 'multiSpeakerTextToSpeechFlow',
    inputSchema: MultiSpeakerInputSchema,
    outputSchema: TTSOutputSchema,
  },
  async (input) => {
    const audioDataUri = await generateMultiSpeakerAudio(
      input.text,
      input.voiceName1,
      input.voiceName2
    );
    return { audioDataUri };
  }
);
\`\`\`

---

## 4. Scenario 3: Image Generation

\`\`\`ts
// src/image-gen.ts
import { z } from 'genkit';
import { ai } from './index';
import { vertexAI } from '@genkit-ai/googleai';
import * as fs from 'fs/promises';
import { parseDataUrl } from 'data-urls';

export const imageGenerationFlow = ai.defineFlow(
  {
    name: 'imageGenerationFlow',
    inputSchema: z
      .string()
      .describe('A detailed description of the image to generate'),
    outputSchema: z.string().describe('Path to the generated .png image file'),
  },
  async (prompt) => {
    const response = await ai.generate({
      model: vertexAI.model('imagen-3.0-generate-002'),
      prompt,
      output: { format: 'media' },
    });

    const imagePart = response.output;
    if (!imagePart?.media?.url) {
      throw new Error('Image generation failed to produce media.');
    }

    const parsed = parseDataUrl(imagePart.media.url);
    if (!parsed) {
      throw new Error('Could not parse image data URL.');
    }

    const outputPath = './output.png';
    await fs.writeFile(outputPath, parsed.body);
    return outputPath;
  }
);
\`\`\`

---

## 5. Scenario 4: Video Generation (Veo3)

\`\`\`ts
// src/video-gen.ts
import { z } from 'genkit';
import { ai } from './index';
import { googleAI } from '@genkit-ai/googleai';
import * as fs from 'fs';
import { Readable } from 'stream';
import fetch from 'node-fetch';

export const videoGenerationFlow = ai.defineFlow(
  {
    name: 'videoGenerationFlow',
    inputSchema: z
      .string()
      .describe('A detailed description for the video scene'),
    outputSchema: z.string().describe('Path to the generated .mp4 video file'),
  },
  async (prompt) => {
    let { operation } = await ai.generate({
      model: googleAI.model('veo-3.0-generate-preview'),
      prompt,
    });

    if (!operation) {
      throw new Error('Expected the model to return an operation.');
    }

    console.log('Video generation started... Polling for completion.');
    while (!operation.done) {
      await new Promise((resolve) => setTimeout(resolve, 5000));
      operation = await ai.checkOperation(operation);
      console.log(
        \`Operation status: \${operation.done ? 'Done' : 'In Progress'}\`
      );
    }

    if (operation.error) {
      throw new Error(\`Video generation failed: \${operation.error.message}\`);
    }

    const video = operation.output?.message?.content.find((p) => !!p.media);
    if (!video?.media?.url) {
      throw new Error(
        'Failed to find the generated video in the operation output.'
      );
    }

    const videoUrl = \`\${video.media.url}&key=\${process.env.GEMINI_API_KEY}\`;
    const videoResponse = await fetch(videoUrl);

    if (!videoResponse.ok || !videoResponse.body) {
      throw new Error(\`Failed to fetch video: \${videoResponse.statusText}\`);
    }

    const outputPath = './output.mp4';
    const fileStream = fs.createWriteStream(outputPath);
    await new Promise((resolve, reject) => {
      Readable.from(videoResponse.body).pipe(fileStream);
      fileStream.on('finish', resolve);
      fileStream.on('error', reject);
    });

    return outputPath;
  }
);
\`\`\`

---

## 6. Running & Inspecting Your Flows

### 6.1 Create a Build Script

Add this to your \`package.json\`:

\`\`\`json
{
  "scripts": {
    "build": "tsc"
  }
}
\`\`\`

### 6.2 Instructions for the User

To test your flows and use the Genkit Developer UI, run the following command from your terminal:

\`\`\`bash
genkit start -- npx tsx --watch src/index.ts
\`\`\`

Visit [http://localhost:4000](http://localhost:4000) to use the Developer UI.

---

## 7. Using Models: correct use of plugins names in model names

When using Genkit models, **prefer the full string form with plugin name up front**:

\`\`\`ts
model: 'googleai/gemini-2.5-flash-preview-tts'; // ✅ RECOMMENDED
\`\`\`

Avoid using just the model name

\`\`\`ts
// ❌ May break:
model: googleAI.model('gemini-2.5-flash-preview-tts');
\`\`\`

Using the full string ensures Genkit resolves the model via the correct plugin and avoids missing \`.media\` in TTS responses.

## 8. Supported Models: latest versions

\`\`\`
| Task                    | Recommended Model                  | Plugin                   |
|-------------------------|------------------------------------|--------------------------|
| Advanced Text/Reasoning | gemini-2.5-pro                     | @genkit-ai/googleai      |
| Fast Text/Chat          | gemini-2.5-flash                   | @genkit-ai/googleai      |
| Text-to-Speech          | gemini-2.5-flash-preview-tts       | @genkit-ai/googleai      |
| Image Generation        | imagen-4.0-generate-preview-06-06  | @genkit-ai/googleai      |
| Video Generation        | veo-3.0-generate-preview           | @genkit-ai/googleai      |
\`\`\`

Tip: Do not use Gemini 1.5 or earlier models for anything, they are out-of-date.

--

# General Guidance

## NPM Dependency Installation Protocol 📦

When you generate or modify any code files (e.g., \`.js\`, \`.ts\`, \`.jsx\`, \`.tsx\`) that reference new libraries, packages, or modules, you **must** install them before proceeding to any build, compilation, or execution step.

Follow this workflow:

1.  **Analyze Dependencies:** After writing or changing a file, identify all third-party dependencies you've introduced.
2.  **Update \`package.json\`:** Ensure these new dependencies are correctly added to the \`package.json\` file.
3.  **Install Dependencies:** Execute the installation command from the project's root directory to download and link the required packages.

### Installation Commands

Always run the appropriate command before any \`npm run build\` or similar script.

\`\`\`bash
# For projects using NPM
npm install

# For projects using Yarn
yarn install

# For projects using PNPM
pnpm install
\`\`\`

This protocol is **critical** to prevent build failures caused by missing modules. Always double-check that dependencies are installed after you add them to the code.
`;
