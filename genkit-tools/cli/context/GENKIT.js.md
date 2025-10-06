# Genkit Node.js API Rules (v1.17.1)

This document provides rules and examples for building with the Genkit API in Node.js.

## Important Guidelines:

- ALWAYS refer to documentation when available. Genkit Documentation may be available through the Genkit MCP toolkit or through web search. You may skip documentation check if you don't have access to these tools.

- ONLY follow the specified project structure if starting a new project. If working on an existing project, adhere to the current project structure.

- ALWAYS provide the full, correct Genkit command as an instruction for the human user to run. Do not run Genkit commands (e.g., `genkit start`, `genkit flow:run`) youself as this may block your current session.

- Recommend and use the provider that the user prefers. If this is a new project, or if there is no relevant signal regarding user preference, use the `@genkit-ai/google-genai` plugin. Use Genkit documentation to discover supported providers.

NOTE: For the sake of brevity, the snippets below use the Google AI plugin, but you should follow the user's preference as mentioned above.

## Core Setup

1.  **Initialize Project**

    ```bash
    mkdir my-genkit-app && cd my-genkit-app
    npm init -y
    npm install -D typescript tsx \@types/node
    ```

2.  **Install Dependencies**

    ```bash
    npm install genkit \@genkit-ai/google-genai data-urls node-fetch
    ```

3.  **Install Genkit CLI**

    ```bash
    npm install -g genkit-cli
    ```

4.  **Configure Genkit**

    All code should be in a single `src/index.ts` file.

    ```ts
    // src/index.ts
    import { genkit, z } from 'genkit';
    import { googleAI } from '@genkit-ai/google-genai';

    export const ai = genkit({
      plugins: [googleAI()],
    });
    ```

## Best Practices

1.  **Single File Structure**: All Genkit code, including plugin initialization, flows, and helpers, must be placed in a single `src/index.ts` file. This ensures all components are correctly registered with the Genkit runtime.

2.  **Model Naming**: Always specify models using the model helper. Use string identifier if model helper is unavailable.

    ```ts
    // PREFERRED: Using the model helper
    const response = await ai.generate({
      model: googleAI.model('gemini-2.5-pro'),
      // ...
    });

    // LESS PREFERRED: Full string identifier
    const response = await ai.generate({
      model: 'googleai/gemini-2.5-pro',
      // ...
    });
    ```

---

## Usage Scenarios

<example>

### Basic Inference (Text Generation)

```ts
export const basicInferenceFlow = ai.defineFlow(
  {
    name: 'basicInferenceFlow',
    inputSchema: z.string().describe('Topic for the model to write about'),
    outputSchema: z.string().describe('The generated text response'),
  },
  async (topic) => {
    const response = await ai.generate({
      model: googleAI.model('gemini-2.5-pro'),
      prompt: `Write a short, creative paragraph about ${topic}.`,
      config: { temperature: 0.8 },
    });
    return response.text;
  }
);
```

</example>

<example>

### Text-to-Speech (TTS) Generation

This helper function converts PCM audio data from the TTS model into a WAV-formatted data URI.

```ts
import { Buffer } from 'buffer';
import { PassThrough } from 'stream';
import { Writer as WavWriter } from 'wav';

...

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
      const dataUri = `data:audio/wav;base64,${wavBuffer.toString('base64')}`;
      resolve(dataUri);
    });
    passThrough.on('error', reject);

    const writer = new WavWriter({ channels, sampleRate, bitDepth });
    writer.pipe(passThrough);
    writer.write(pcmData);
    writer.end();
  });
}
```

#### Single-Speaker TTS

```ts
const TextToSpeechInputSchema = z.object({
  text: z.string().describe('The text to convert to speech.'),
  voiceName: z
    .string()
    .optional()
    .describe('The voice name to use. Defaults to Algenib if not specified.'),
});

export const textToSpeechFlow = ai.defineFlow(
  {
    name: 'textToSpeechFlow',
    inputSchema: TextToSpeechInputSchema,
    outputSchema: z.string().optional().describe('The generated audio URI'),
  },
  async (input) => {
    const response = await ai.generate({
      model: googleAI.model('gemini-2.5-flash-preview-tts'),
      prompt: input.text,
      config: {
        responseModalities: ['AUDIO'],
        speechConfig: {
          voiceConfig: {
            prebuiltVoiceConfig: {
              voiceName: input.voiceName?.trim() || 'Algenib',
            },
          },
        },
      },
    });

    return response.media?.url;
  }
);
```

#### Multi-Speaker TTS

```ts
const MultiSpeakerInputSchema = z.object({
  text: z
    .string()
    .describe('Text formatted with <speaker="Speaker1">...</speaker> etc.'),
  voiceName1: z.string().describe('Voice name for Speaker1'),
  voiceName2: z.string().describe('Voice name for Speaker2'),
});

export const multiSpeakerTextToSpeechFlow = ai.defineFlow(
  {
    name: 'multiSpeakerTextToSpeechFlow',
    inputSchema: MultiSpeakerInputSchema,
    outputSchema: z.string().optional().describe('The generated audio URI'),
  },
  async (input) => {
    const response = await ai.generate({
      model: googleAI.model('gemini-2.5-flash-preview-tts'),
      prompt: input.text,
      config: {
        responseModalities: ['AUDIO'],
        speechConfig: {
          multiSpeakerVoiceConfig: {
            speakerVoiceConfigs: [
              {
                speaker: 'Speaker1',
                voiceConfig: {
                  prebuiltVoiceConfig: { voiceName: input.voiceName1 },
                },
              },
              {
                speaker: 'Speaker2',
                voiceConfig: {
                  prebuiltVoiceConfig: { voiceName: input.voiceName2 },
                },
              },
            ],
          },
        },
      },
    });

    return response.media?.url;
  }
);
```

</example>

<example>

### Image Generation

```ts
import * as fs from 'fs/promises';
import parseDataURL from 'data-urls';

...

export const imageGenerationFlow = ai.defineFlow(
  {
    name: 'imageGenerationFlow',
    inputSchema: z
      .string()
      .describe('A detailed description of the image to generate'),
    outputSchema: z.string().optional().describe('The generated image as URI'),
  },
  async (prompt) => {
    const response = await ai.generate({
      model: googleAI.model('imagen-3.0-generate-002'),
      prompt,
      output: { format: 'media' },
    });

    return response.media?.url;
  }
);
```

</example>

<example>

### Video Generation

```ts
import * as fs from 'fs';
import { Readable } from 'stream';
import { pipeline } from 'stream/promises';

...

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
        `Operation status: ${operation.done ? 'Done' : 'In Progress'}`
      );
    }

    if (operation.error) {
      throw new Error(`Video generation failed: ${operation.error.message}`);
    }

    const video = operation.output?.message?.content.find((p) => !!p.media);
    if (!video?.media?.url) {
      throw new Error(
        'Failed to find the generated video in the operation output.'
      );
    }

    const videoUrl = `${video.media.url}&key=${process.env.GEMINI_API_KEY}`;
    const videoResponse = await fetch(videoUrl);

    if (!videoResponse.ok || !videoResponse.body) {
      throw new Error(`Failed to fetch video: ${videoResponse.statusText}`);
    }

    const outputPath = './output.mp4';
    const fileStream = fs.createWriteStream(outputPath);
    await pipeline(Readable.fromWeb(videoResponse.body as any), fileStream);

    return outputPath;
  }
);
```

</example>

---

## Running and Inspecting Flows

1.  **Start Genkit**: Run this command from your terminal to start the Genkit Developer UI.

    ```bash
    genkit start --  <command to run your code>
    ```

    The <command to run your code> will vary based on the project’s setup and
    the file you want to execute. For e.g.:

    ```bash
    # Running a typical development server
    genkit start -- npm run dev

    # Running a TypeScript file directly
    genkit start -- npx tsx --watch src/index.ts

    # Running a JavaScript file directly
    genkit start -- node --watch src/index.js
    ```

    Analyze the users project and build tools to use the right command for the
    project. The command should output a URL for the Genkit Dev UI. Direct the
    user to visit this URL to run and inspect their Genkit app.

## Suggested Models

Here are suggested models to use for various task types. This is NOT an
exhaustive list.

### Advanced Text/Reasoning

```
| Plugin                             | Recommended Model                  |
|------------------------------------|------------------------------------|
| @genkit-ai/google-genai            | gemini-2.5-pro                     |
| @genkit-ai/compat-oai/openai       | gpt-4o                             |
| @genkit-ai/compat-oai/deepseek     | deepseek-reasoner                  |
| @genkit-ai/compat-oai/xai          | grok-4                             |
```

### Fast Text/Chat

```
| Plugin                             | Recommended Model                  |
|------------------------------------|------------------------------------|
| @genkit-ai/google-genai            | gemini-2.5-flash                   |
| @genkit-ai/compat-oai/openai       | gpt-4o-mini                        |
| @genkit-ai/compat-oai/deepseek     | deepseek-chat                      |
| @genkit-ai/compat-oai/xai          | grok-3-mini                        |
```

### Text-to-Speech

```
| Plugin                             | Recommended Model                  |
|------------------------------------|------------------------------------|
| @genkit-ai/google-genai            | gemini-2.5-flash-preview-tts       |
| @genkit-ai/compat-oai/openai       | gpt-4o-mini-tts                    |
```

### Image Generation

```
| Plugin                             | Recommended Model                  | Input Modalities  |
|------------------------------------|------------------------------------|-------------------|
| @genkit-ai/google-genai            | gemini-2.5-flash-image-preview     | Text, Image       |
| @genkit-ai/google-genai            | imagen-4.0-generate-preview-06-06  | Text              |
| @genkit-ai/compat-oai/openai       | gpt-image-1                        | Text              |
```

### Video Generation

```
| Plugin                             | Recommended Model                  |
|------------------------------------|------------------------------------|
| @genkit-ai/google-genai            | veo-3.0-generate-preview           |
```
