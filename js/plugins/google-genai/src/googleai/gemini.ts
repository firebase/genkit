/**
 * Copyright 2025 Google LLC
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

import {
  ActionMetadata,
  Genkit,
  GenkitError,
  modelActionMetadata,
  z,
} from 'genkit';
import {
  GenerationCommonConfigSchema,
  ModelAction,
  ModelInfo,
  ModelMiddleware,
  ModelReference,
  getBasicUsageStats,
  modelRef,
} from 'genkit/model';
import { downloadRequestMedia } from 'genkit/model/middleware';
import { runInNewSpan } from 'genkit/tracing';
import {
  fromGeminiCandidate,
  toGeminiFunctionModeEnum,
  toGeminiMessage,
  toGeminiSystemInstruction,
  toGeminiTool,
} from '../common/converters';
import { cleanSchema } from '../common/utils';
import {
  generateContent,
  generateContentStream,
  getGoogleAIUrl,
} from './client';
import {
  ClientOptions,
  Content as GeminiMessage,
  GenerateContentRequest,
  GenerateContentResponse,
  GenerationConfig,
  GoogleAIPluginOptions,
  GoogleSearchRetrievalTool,
  Model,
  SafetySetting,
  Tool,
  ToolConfig,
} from './types';
import { calculateApiKey, checkApiKey, modelName } from './utils';

/**
 * See https://ai.google.dev/gemini-api/docs/safety-settings#safety-filters.
 */
const SafetySettingsSchema = z.object({
  category: z.enum([
    'HARM_CATEGORY_UNSPECIFIED',
    'HARM_CATEGORY_HATE_SPEECH',
    'HARM_CATEGORY_SEXUALLY_EXPLICIT',
    'HARM_CATEGORY_HARASSMENT',
    'HARM_CATEGORY_DANGEROUS_CONTENT',
  ]),
  threshold: z.enum([
    'BLOCK_LOW_AND_ABOVE',
    'BLOCK_MEDIUM_AND_ABOVE',
    'BLOCK_ONLY_HIGH',
    'BLOCK_NONE',
  ]),
});

const VoiceConfigSchema = z
  .object({
    prebuiltVoiceConfig: z
      .object({
        // TODO: Make this an array of objects so we can also specify the description
        // for each voiceName.
        voiceName: z
          .union([
            z.enum([
              'Zephyr',
              'Puck',
              'Charon',
              'Kore',
              'Fenrir',
              'Leda',
              'Orus',
              'Aoede',
              'Callirrhoe',
              'Autonoe',
              'Enceladus',
              'Iapetus',
              'Umbriel',
              'Algieba',
              'Despina',
              'Erinome',
              'Algenib',
              'Rasalgethi',
              'Laomedeia',
              'Achernar',
              'Alnilam',
              'Schedar',
              'Gacrux',
              'Pulcherrima',
              'Achird',
              'Zubenelgenubi',
              'Vindemiatrix',
              'Sadachbia',
              'Sadaltager',
              'Sulafat',
            ]),
            // To allow any new string values
            z.string(),
          ])
          .describe('Name of the preset voice to use')
          .optional(),
      })
      .describe('Configuration for the prebuilt speaker to use')
      .passthrough()
      .optional(),
  })
  .describe('Configuration for the voice to use')
  .passthrough();

export const GeminiConfigSchema = GenerationCommonConfigSchema.extend({
  apiKey: z
    .string()
    .describe('Overrides the plugin-configured API key, if specified.')
    .optional(),
  safetySettings: z
    .array(SafetySettingsSchema)
    .describe(
      'Adjust how likely you are to see responses that could be harmful. ' +
        'Content is blocked based on the probability that it is harmful.'
    )
    .optional(),
  codeExecution: z
    .union([z.boolean(), z.object({}).strict()])
    .describe('Enables the model to generate and run code.')
    .optional(),
  contextCache: z
    .boolean()
    .describe(
      'Context caching allows you to save and reuse precomputed input ' +
        'tokens that you wish to use repeatedly.'
    )
    .optional(),
  functionCallingConfig: z
    .object({
      mode: z.enum(['MODE_UNSPECIFIED', 'AUTO', 'ANY', 'NONE']).optional(),
      allowedFunctionNames: z.array(z.string()).optional(),
    })
    .describe(
      'Controls how the model uses the provided tools (function declarations). ' +
        'With AUTO (Default) mode, the model decides whether to generate a ' +
        'natural language response or suggest a function call based on the ' +
        'prompt and context. With ANY, the model is constrained to always ' +
        'predict a function call and guarantee function schema adherence. ' +
        'With NONE, the model is prohibited from making function calls.'
    )
    .optional(),
  responseModalities: z
    .array(z.enum(['TEXT', 'IMAGE', 'AUDIO']))
    .describe(
      'The modalities to be used in response. Only supported for ' +
        "'gemini-2.0-flash-exp' model at present."
    )
    .optional(),
  googleSearchRetrieval: z
    .union([z.boolean(), z.object({}).passthrough()])
    .describe(
      'Retrieve public web data for grounding, powered by Google Search.'
    )
    .optional(),
}).passthrough();
export type GeminiConfigSchemaType = typeof GeminiConfigSchema;
export type GeminiConfig = z.infer<GeminiConfigSchemaType>;

export const GeminiTtsConfigSchema = GeminiConfigSchema.extend({
  speechConfig: z
    .object({
      voiceConfig: VoiceConfigSchema.optional(),
      multiSpeakerVoiceConfig: z
        .object({
          speakerVoiceConfigs: z
            .array(
              z
                .object({
                  speaker: z.string().describe('Name of the speaker to use'),
                  voiceConfig: VoiceConfigSchema,
                })
                .describe(
                  'Configuration for a single speaker in a multi speaker setup'
                )
                .passthrough()
            )
            .describe('Configuration for all the enabled speaker voices'),
        })
        .describe('Configuration for multi-speaker setup')
        .passthrough()
        .optional(),
    })
    .describe('Speech generation config')
    .passthrough()
    .optional(),
}).passthrough();
export type GeminiTtsConfigSchemaType = typeof GeminiTtsConfigSchema;
export type GeminiTtsConfig = z.infer<GeminiTtsConfigSchemaType>;

// This contains all the Gemini config schema types
type ConfigSchemaType = GeminiConfigSchemaType | GeminiTtsConfigSchemaType;

function commonRef(
  name: string,
  info?: ModelInfo,
  configSchema: ConfigSchemaType = GeminiConfigSchema
): ModelReference<ConfigSchemaType> {
  return modelRef({
    name: `googleai/${name}`,
    configSchema,
    info: info ?? {
      supports: {
        multiturn: true,
        media: true,
        tools: true,
        toolChoice: true,
        systemRole: true,
        constrained: 'no-tools',
        output: ['text', 'json'],
      },
    },
  });
}

const GENERIC_MODEL = commonRef('gemini');
const GENERIC_TTS_MODEL = commonRef('gemini-tts', {
  supports: {
    multiturn: false,
    media: false,
    tools: false,
    toolChoice: false,
    systemRole: false,
    constrained: 'no-tools',
  },
});

const KNOWN_MODELS = {
  'gemini-2.0-flash': commonRef('gemini-2.0-flash'),
  'gemini-2.0-flash-lite': commonRef('gemini-2.0-flash-lite'),
  'gemini-2.0-pro-exp-02-05': commonRef('gemini-2.0-pro-exp-02-05'),
  'gemini-2.0-flash-exp': commonRef('gemini-2.0-flash-exp'),
  'gemini-2.5-pro-exp-03-25': commonRef('gemini-2.5-pro-exp-03-25'),
  'gemini-2.5-pro-preview-03-25': commonRef('gemini-2.5-pro-preview-03-25'),
  'gemini-2.5-flash-preview-04-17': commonRef('gemini-2.5-flash-preview-04-17'),
  'gemini-2.5-flash-preview-tts': commonRef(
    'gemini-2.5-flash-preview-tts',
    { ...GENERIC_TTS_MODEL.info },
    GeminiTtsConfigSchema
  ),
  'gemini-2.5-pro-preview-tts': commonRef(
    'gemini-2.5-pro-preview-tts',
    { ...GENERIC_TTS_MODEL.info },
    GeminiTtsConfigSchema
  ),
} as const;
export type KnownModels = keyof typeof KNOWN_MODELS; // For autocomplete

// For conditional types in index.ts model()
export type TTSModelName = `gemini-${string}-tts`;
export function isTTSModelName(value: string): value is TTSModelName {
  return value.startsWith('gemini-') && value.endsWith('-tts');
}

export function model(
  version: string,
  config: GeminiConfig | GeminiTtsConfig = {}
): ModelReference<ConfigSchemaType> {
  const name = modelName(version);
  if (!name) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: 'Not able to create modelReference for empty model version',
    });
  }

  if (isTTSModelName(name)) {
    return modelRef({
      name: `googleai/${name}`,
      version: name,
      config,
      configSchema: GeminiTtsConfigSchema,
      info: { ...GENERIC_TTS_MODEL.info },
    });
  }

  return modelRef({
    name: `googleai/${name}`,
    version: name,
    config,
    configSchema: GeminiConfigSchema,
    info: { ...GENERIC_MODEL.info },
  });
}

// Takes a full list of models, filters for current Gemini models only
// and returns a modelActionMetadata for each.
export function listActions(models: Model[]): ActionMetadata[] {
  return (
    models
      .filter((m) => m.supportedGenerationMethods.includes('generateContent'))
      // Filter out deprecated
      .filter((m) => !m.description || !m.description.includes('deprecated'))
      .map((m) => {
        const ref = model(m.name);
        return modelActionMetadata({
          name: ref.name,
          info: ref.info,
          configSchema: ref.configSchema,
        });
      })
  );
}

export function defineKnownModels(ai: Genkit, options?: GoogleAIPluginOptions) {
  for (const name of Object.keys(KNOWN_MODELS)) {
    defineModel(ai, name, options);
  }
}

/**
 * Defines a new GoogleAI Gemini model.
 */
export function defineModel(
  ai: Genkit,
  name: string,
  pluginOptions?: GoogleAIPluginOptions
): ModelAction {
  checkApiKey(pluginOptions?.apiKey);
  const ref = model(name);

  const middleware: ModelMiddleware[] = [];
  if (ref.info?.supports?.media) {
    // the gemini api doesn't support downloading media from http(s)
    middleware.push(
      downloadRequestMedia({
        maxBytes: 1024 * 1024 * 10,
        // don't downlaod files that have been uploaded using the Files API
        filter: (part) => {
          try {
            const url = new URL(part.media.url);
            if (
              // Gemini can handle these URLs
              [
                'generativelanguage.googleapis.com',
                'www.youtube.com',
                'youtube.com',
                'youtu.be',
              ].includes(url.hostname)
            )
              return false;
          } catch {}
          return true;
        },
      })
    );
  }

  return ai.defineModel(
    {
      name: ref.name,
      ...ref.info,
      configSchema: ref.configSchema,
      use: middleware,
    },
    async (request, sendChunk) => {
      const clientOptions: ClientOptions = {
        apiVersion: pluginOptions?.apiVersion,
        baseUrl: pluginOptions?.baseUrl,
      };

      // Make a copy so that modifying the request will not produce side-effects
      const messages = [...request.messages];
      if (messages.length === 0) throw new Error('No messages provided.');

      // Gemini does not support messages with role system and instead expects
      // systemInstructions to be provided as a separate input. The first
      // message detected with role=system will be used for systemInstructions.
      let systemInstruction: GeminiMessage | undefined = undefined;
      const systemMessage = messages.find((m) => m.role === 'system');
      if (systemMessage) {
        messages.splice(messages.indexOf(systemMessage), 1);
        systemInstruction = toGeminiSystemInstruction(systemMessage);
      }

      const tools: Tool[] = [];
      if (request.tools?.length) {
        tools.push({
          functionDeclarations: request.tools.map(toGeminiTool),
        });
      }

      const requestOptions: z.infer<ConfigSchemaType> = {
        ...request.config,
      };
      const {
        apiKey: apiKeyFromConfig,
        safetySettings: safetySettingsFromConfig,
        codeExecution: codeExecutionFromConfig,
        version: versionFromConfig,
        functionCallingConfig,
        googleSearchRetrieval,
        tools: toolsFromConfig,
        ...restOfConfigOptions
      } = requestOptions;

      if (codeExecutionFromConfig) {
        tools.push({
          codeExecution:
            codeExecutionFromConfig === true ? {} : codeExecutionFromConfig,
        });
      }

      if (toolsFromConfig) {
        tools.push(...(toolsFromConfig as any[]));
      }

      if (googleSearchRetrieval) {
        tools.push({
          googleSearch:
            googleSearchRetrieval === true ? {} : googleSearchRetrieval,
        } as GoogleSearchRetrievalTool);
      }

      let toolConfig: ToolConfig | undefined;
      if (functionCallingConfig) {
        toolConfig = {
          functionCallingConfig: {
            allowedFunctionNames: functionCallingConfig.allowedFunctionNames,
            mode: toGeminiFunctionModeEnum(functionCallingConfig.mode),
          },
        };
      } else if (request.toolChoice) {
        toolConfig = {
          functionCallingConfig: {
            mode: toGeminiFunctionModeEnum(request.toolChoice),
          },
        };
      }

      // Cannot use tools with JSON mode
      const jsonMode =
        request.output?.format === 'json' ||
        (request.output?.contentType === 'application/json' &&
          tools.length === 0);

      const generationConfig: GenerationConfig = {
        ...restOfConfigOptions,
        candidateCount: request.candidates || undefined,
        responseMimeType: jsonMode ? 'application/json' : undefined,
      };

      if (request.output?.constrained && jsonMode) {
        generationConfig.responseSchema = cleanSchema(request.output.schema);
      }

      const msg = toGeminiMessage(messages[messages.length - 1], ref);

      let generateContentRequest: GenerateContentRequest = {
        systemInstruction,
        generationConfig,
        tools: tools.length ? tools : undefined,
        toolConfig,
        safetySettings: safetySettingsFromConfig?.filter(
          (setting) => setting.category !== 'HARM_CATEGORY_UNSPECIFIED'
        ) as SafetySetting[],
        contents: messages.map((message) => toGeminiMessage(message, ref)),
      };

      const modelVersion = (versionFromConfig || ref.version) as string;

      const generateApiKey = calculateApiKey(
        pluginOptions?.apiKey,
        requestOptions.apiKey
      );

      const callGemini = async () => {
        let response: GenerateContentResponse;

        if (sendChunk) {
          const result = await generateContentStream(
            generateApiKey,
            modelVersion,
            generateContentRequest,
            clientOptions
          );

          for await (const item of result.stream) {
            item.candidates?.forEach((candidate) => {
              const c = fromGeminiCandidate(candidate);
              sendChunk({
                index: c.index,
                content: c.message.content,
              });
            });
          }
          response = await result.response;
        } else {
          response = await generateContent(
            generateApiKey,
            modelVersion,
            generateContentRequest,
            clientOptions
          );
        }

        const candidates = response.candidates || [];
        if (response.candidates?.['undefined']) {
          candidates.push(response.candidates['undefined']);
        }
        if (!candidates.length) {
          throw new GenkitError({
            status: 'FAILED_PRECONDITION',
            message: 'No valid candidates returned.',
          });
        }

        const candidateData = candidates.map(fromGeminiCandidate) || [];

        return {
          candidates: candidateData,
          custom: response,
          usage: {
            ...getBasicUsageStats(request.messages, candidateData),
            inputTokens: response.usageMetadata?.promptTokenCount,
            outputTokens: response.usageMetadata?.candidatesTokenCount,
            totalTokens: response.usageMetadata?.totalTokenCount,
            cachedContentTokens:
              response.usageMetadata?.cachedContentTokenCount,
          },
        };
      };

      // If debugTraces is enabled, we wrap the actual model call with a span, add raw
      // API params as for input.
      return pluginOptions?.experimental_debugTraces
        ? await runInNewSpan(
            ai.registry,
            {
              metadata: {
                name: sendChunk ? 'sendMessageStream' : 'sendMessage',
              },
            },
            async (metadata) => {
              metadata.input = {
                apiEndpoint: getGoogleAIUrl({
                  resourcePath: '',
                  clientOptions,
                }),
                cache: {},
                model: modelVersion,
                generateContentOptions: generateContentRequest,
                parts: msg.parts,
                options: clientOptions,
              };
              const response = await callGemini();
              metadata.output = response.custom;
              return response;
            }
          )
        : await callGemini();
    }
  );
}

export const TEST_ONLY = { KNOWN_MODELS };
