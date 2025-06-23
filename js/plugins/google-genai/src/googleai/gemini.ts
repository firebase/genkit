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

import { Genkit, GenkitError, z } from 'genkit';
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
import { cleanSchema, nearestModelRef } from '../common/utils';
import {
  generateContent,
  generateContentStream,
  getGoogleAIUrl,
} from './client';
import {
  Content as GeminiMessage,
  GenerateContentRequest,
  GenerateContentResponse,
  GenerationConfig,
  GoogleSearchRetrievalTool,
  RequestOptions,
  SafetySetting,
  Tool,
  ToolConfig,
} from './types';
import { getApiKeyFromEnvVar } from './utils';

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
export type GeminiConfig = z.infer<typeof GeminiConfigSchema>;

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

// For commonRef
type ConfigSchema = typeof GeminiConfigSchema | typeof GeminiTtsConfigSchema;

const TTS_MODEL_INFO: ModelInfo = {
  supports: {
    multiturn: false,
    media: false,
    tools: false,
    toolChoice: false,
    systemRole: false,
    constrained: 'no-tools',
  },
};

function commonRef(
  name: string,
  info?: ModelInfo,
  configSchema: ConfigSchema = GeminiConfigSchema
): ModelReference<ConfigSchema> {
  return modelRef({
    name: `googleai/${name}`,
    info: info ?? {
      supports: {
        multiturn: true,
        media: true,
        tools: true,
        toolChoice: true,
        systemRole: true,
        constrained: 'no-tools',
      },
    },
    configSchema,
  });
}

export const KNOWN_GEMINI_MODELS = {
  'gemini-2.0-flash': commonRef('gemini-2.0-flash'),
  'gemini-2.0-flash-lite': commonRef('gemini-2.0-flash-lite'),
  'gemini-2.0-pro-exp-02-05': commonRef('gemini-2.0-pro-exp-02-05'),
  'gemini-2.0-flash-exp': commonRef('gemini-2.0-flash-exp'),
  'gemini-2.5-pro-exp-03-25': commonRef('gemini-2.5-pro-exp-03-25'),
  'gemini-2.5-pro-preview-03-25': commonRef('gemini-2.5-pro-preview-03-25'),
  'gemini-2.5-flash-preview-04-17': commonRef('gemini-2.5-flash-preview-04-17'),
  'gemini-2.5-flash-preview-tts': commonRef(
    'gemini-2.5-flash-preview-tts',
    TTS_MODEL_INFO,
    GeminiTtsConfigSchema
  ),
  'gemini-2.5-pro-preview-tts': commonRef(
    'gemini-2.5-pro-preview-tts',
    TTS_MODEL_INFO,
    GeminiTtsConfigSchema
  ),
} as const;

export const GENERIC_GEMINI_MODEL = commonRef('gemini');

/**
 * Known model names, to allow code completion for convenience. Allows other model names.
 */
export type GeminiVersionString =
  | keyof typeof KNOWN_GEMINI_MODELS
  | (string & {});

/**
 * Returns a reference to a model that can be used in generate calls.
 *
 * ```js
 * await ai.generate({
 *   prompt: 'hi',
 *   model: gemini('gemini-2.5-flash')
 * });
 * ```
 */
export function gemini(
  version: GeminiVersionString,
  options: GeminiConfig = {}
): ModelReference<typeof GeminiConfigSchema> {
  const nearestModel = nearestModelRef(
    version,
    KNOWN_GEMINI_MODELS,
    GENERIC_GEMINI_MODEL
  );
  return modelRef({
    name: `googleai/${version}`,
    config: options,
    configSchema: nearestModel.configSchema,
    info: {
      ...nearestModel.info,
    },
  });
}

/**
 * Defines a new GoogleAI Gemini model.
 */
export function defineGeminiModel({
  ai,
  name,
  apiKey: apiKeyOption,
  apiVersion,
  baseUrl,
  info,
  defaultConfig,
  debugTraces,
}: {
  ai: Genkit;
  name: string;
  apiKey?: string | false;
  apiVersion?: string;
  baseUrl?: string;
  info?: ModelInfo;
  defaultConfig?: GeminiConfig;
  debugTraces?: boolean;
}): ModelAction {
  let apiKey: string | undefined;
  // DO NOT infer API key from environment variable if plugin was configured with `{apiKey: false}`.
  if (apiKeyOption !== false) {
    apiKey = apiKeyOption || getApiKeyFromEnvVar();
    if (!apiKey) {
      throw new GenkitError({
        status: 'FAILED_PRECONDITION',
        message:
          'Please pass in the API key or set the GEMINI_API_KEY or GOOGLE_API_KEY environment variable.\n' +
          'For more details see https://firebase.google.com/docs/genkit/plugins/google-genai',
      });
    }
  }

  const apiModelName = name.startsWith('googleai/')
    ? name.substring('googleai/'.length)
    : name;

  const model: ModelReference<z.ZodTypeAny> =
    KNOWN_GEMINI_MODELS[apiModelName] ??
    modelRef({
      name: `googleai/${apiModelName}`,
      info: {
        supports: {
          multiturn: true,
          media: true,
          tools: true,
          systemRole: true,
          output: ['text', 'json'],
        },
        ...info,
      },
      configSchema: GeminiConfigSchema,
    });

  const middleware: ModelMiddleware[] = [];
  if (model.info?.supports?.media) {
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
      name: model.name,
      ...model.info,
      configSchema: model.configSchema,
      use: middleware,
    },
    async (request, sendChunk) => {
      const options: RequestOptions = {
        apiVersion,
        baseUrl,
      };
      const requestConfig: z.infer<typeof GeminiConfigSchema> = {
        ...defaultConfig,
        ...request.config,
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

      const {
        apiKey: apiKeyFromConfig,
        safetySettings: safetySettingsFromConfig,
        codeExecution: codeExecutionFromConfig,
        version: versionFromConfig,
        functionCallingConfig,
        googleSearchRetrieval,
        tools: toolsFromConfig,
        ...restOfConfigOptions
      } = requestConfig;

      if (codeExecutionFromConfig) {
        tools.push({
          codeExecution:
            request.config.codeExecution === true
              ? {}
              : request.config.codeExecution,
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

      const msg = toGeminiMessage(messages[messages.length - 1], model);

      let generateContentRequest: GenerateContentRequest = {
        systemInstruction,
        generationConfig,
        tools: tools.length ? tools : undefined,
        toolConfig,
        safetySettings: safetySettingsFromConfig?.filter(
          (setting) => setting.category !== 'HARM_CATEGORY_UNSPECIFIED'
        ) as SafetySetting[],
        contents: messages.map((message) => toGeminiMessage(message, model)),
      };

      const modelVersion = (versionFromConfig ||
        model.version ||
        apiModelName) as string;

      apiKey = apiKeyFromConfig || apiKey;
      if (!apiKey) {
        throw new GenkitError({
          status: 'INVALID_ARGUMENT',
          message:
            'GoogleAI plugin was initialized with {apiKey: false} but no apiKey configuration was passed at call time.',
        });
      }

      const callGemini = async () => {
        let response: GenerateContentResponse;

        if (sendChunk) {
          const result = await generateContentStream(
            apiKey!,
            modelVersion,
            generateContentRequest,
            options
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
            apiKey!,
            modelVersion,
            generateContentRequest,
            options
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
      return debugTraces
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
                  requestOptions: options,
                }),
                cache: {},
                model: modelVersion,
                generateContentOptions: generateContentRequest,
                parts: msg.parts,
                options,
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
