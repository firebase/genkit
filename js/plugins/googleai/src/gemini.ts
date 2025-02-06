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

import {
  FileDataPart,
  FunctionCallingMode,
  FunctionCallPart,
  FunctionDeclaration,
  FunctionResponsePart,
  GenerateContentCandidate as GeminiCandidate,
  Content as GeminiMessage,
  Part as GeminiPart,
  GenerateContentResponse,
  GenerationConfig,
  GenerativeModel,
  GoogleGenerativeAI,
  InlineDataPart,
  RequestOptions,
  SchemaType,
  StartChatParams,
  Tool,
  ToolConfig,
} from '@google/generative-ai';
import {
  Genkit,
  GENKIT_CLIENT_HEADER,
  GenkitError,
  JSONSchema,
  z,
} from 'genkit';
import {
  CandidateData,
  GenerationCommonConfigSchema,
  getBasicUsageStats,
  MediaPart,
  MessageData,
  ModelAction,
  ModelInfo,
  ModelMiddleware,
  modelRef,
  ModelReference,
  Part,
  ToolDefinitionSchema,
  ToolRequestPart,
  ToolResponsePart,
} from 'genkit/model';
import {
  downloadRequestMedia,
  simulateSystemPrompt,
} from 'genkit/model/middleware';
import process from 'process';
import { handleCacheIfNeeded } from './context-caching';
import { extractCacheConfig } from './context-caching/utils';

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

export const GeminiConfigSchema = GenerationCommonConfigSchema.extend({
  safetySettings: z.array(SafetySettingsSchema).optional(),
  codeExecution: z.union([z.boolean(), z.object({}).strict()]).optional(),
  contextCache: z.boolean().optional(),
  functionCallingConfig: z
    .object({
      mode: z.enum(['MODE_UNSPECIFIED', 'AUTO', 'ANY', 'NONE']).optional(),
      allowedFunctionNames: z.array(z.string()).optional(),
    })
    .optional(),
});
export type GeminiConfig = z.infer<typeof GeminiConfigSchema>;

export const gemini10Pro = modelRef({
  name: 'googleai/gemini-1.0-pro',
  info: {
    label: 'Google AI - Gemini Pro',
    versions: ['gemini-pro', 'gemini-1.0-pro-latest', 'gemini-1.0-pro-001'],
    supports: {
      multiturn: true,
      media: false,
      tools: true,
      toolChoice: true,
      systemRole: true,
      constrained: 'no-tools',
    },
  },
  configSchema: GeminiConfigSchema,
});

export const gemini15Pro = modelRef({
  name: 'googleai/gemini-1.5-pro',
  info: {
    label: 'Google AI - Gemini 1.5 Pro',
    supports: {
      multiturn: true,
      media: true,
      tools: true,
      toolChoice: true,
      systemRole: true,
      constrained: 'no-tools',
    },
    versions: [
      'gemini-1.5-pro-latest',
      'gemini-1.5-pro-001',
      'gemini-1.5-pro-002',
    ],
  },
  configSchema: GeminiConfigSchema,
});

export const gemini15Flash = modelRef({
  name: 'googleai/gemini-1.5-flash',
  info: {
    label: 'Google AI - Gemini 1.5 Flash',
    supports: {
      multiturn: true,
      media: true,
      tools: true,
      toolChoice: true,
      systemRole: true,
      constrained: 'no-tools',
      // @ts-ignore
      contextCache: true,
    },
    versions: [
      'gemini-1.5-flash-latest',
      'gemini-1.5-flash-001',
      'gemini-1.5-flash-002',
    ],
  },
  configSchema: GeminiConfigSchema,
});

export const gemini15Flash8b = modelRef({
  name: 'googleai/gemini-1.5-flash-8b',
  info: {
    label: 'Google AI - Gemini 1.5 Flash',
    supports: {
      multiturn: true,
      media: true,
      tools: true,
      toolChoice: true,
      systemRole: true,
      constrained: 'no-tools',
    },
    versions: ['gemini-1.5-flash-8b-latest', 'gemini-1.5-flash-8b-001'],
  },
  configSchema: GeminiConfigSchema,
});

export const gemini20Flash = modelRef({
  name: 'googleai/gemini-2.0-flash',
  info: {
    label: 'Google AI - Gemini 2.0 Flash',
    versions: [],
    supports: {
      multiturn: true,
      media: true,
      tools: true,
      toolChoice: true,
      systemRole: true,
      constrained: 'no-tools',
    },
  },
  configSchema: GeminiConfigSchema,
});

export const SUPPORTED_V1_MODELS = {
  'gemini-1.0-pro': gemini10Pro,
};

export const SUPPORTED_V15_MODELS = {
  'gemini-1.5-pro': gemini15Pro,
  'gemini-1.5-flash': gemini15Flash,
  'gemini-1.5-flash-8b': gemini15Flash8b,
  'gemini-2.0-flash': gemini20Flash,
};

export const GENERIC_GEMINI_MODEL = modelRef({
  name: 'googleai/gemini',
  configSchema: GeminiConfigSchema,
  info: {
    label: 'Google Gemini',
    supports: {
      multiturn: true,
      media: true,
      tools: true,
      toolChoice: true,
      systemRole: true,
      constrained: 'no-tools',
    },
  },
});

export const SUPPORTED_GEMINI_MODELS = {
  ...SUPPORTED_V1_MODELS,
  ...SUPPORTED_V15_MODELS,
} as const;

function longestMatchingPrefix(version: string, potentialMatches: string[]) {
  return potentialMatches
    .filter((p) => version.startsWith(p))
    .reduce(
      (longest, current) =>
        current.length > longest.length ? current : longest,
      ''
    );
}

/**
 * Known model names, to allow code completion for convenience. Allows other model names.
 */
export type GeminiVersionString =
  | keyof typeof SUPPORTED_GEMINI_MODELS
  | (string & {});

/**
 * Returns a reference to a model that can be used in generate calls.
 *
 * ```js
 * await ai.generate({
 *   prompt: 'hi',
 *   model: gemini('gemini-1.5-flash')
 * });
 * ```
 */
export function gemini(
  version: GeminiVersionString,
  options: GeminiConfig = {}
): ModelReference<typeof GeminiConfigSchema> {
  const nearestModel = nearestGeminiModelRef(version);
  return modelRef({
    name: `googleai/${version}`,
    config: options,
    configSchema: GeminiConfigSchema,
    info: {
      ...nearestModel.info,
      // If exact suffix match for a known model, use its label, otherwise create a new label
      label: nearestModel.name.endsWith(version)
        ? nearestModel.info?.label
        : `Google AI - ${version}`,
    },
  });
}

function nearestGeminiModelRef(
  version: GeminiVersionString,
  options: GeminiConfig = {}
): ModelReference<typeof GeminiConfigSchema> {
  const matchingKey = longestMatchingPrefix(
    version,
    Object.keys(SUPPORTED_GEMINI_MODELS)
  );
  if (matchingKey) {
    return SUPPORTED_GEMINI_MODELS[matchingKey].withConfig({
      ...options,
      version,
    });
  }
  return GENERIC_GEMINI_MODEL.withConfig({ ...options, version });
}

function toGeminiRole(
  role: MessageData['role'],
  model?: ModelReference<z.ZodTypeAny>
): string {
  switch (role) {
    case 'user':
      return 'user';
    case 'model':
      return 'model';
    case 'system':
      if (model && SUPPORTED_V15_MODELS[model.name]) {
        // We should have already pulled out the supported system messages,
        // anything remaining is unsupported; throw an error.
        throw new Error(
          'system role is only supported for a single message in the first position'
        );
      } else {
        throw new Error('system role is not supported');
      }
    case 'tool':
      return 'function';
    default:
      return 'user';
  }
}

function convertSchemaProperty(property) {
  if (!property || !property.type) {
    return null;
  }
  if (property.type === 'object') {
    const nestedProperties = {};
    Object.keys(property.properties).forEach((key) => {
      nestedProperties[key] = convertSchemaProperty(property.properties[key]);
    });
    return {
      type: SchemaType.OBJECT,
      properties: nestedProperties,
      required: property.required,
    };
  } else if (property.type === 'array') {
    return {
      type: SchemaType.ARRAY,
      items: convertSchemaProperty(property.items),
    };
  } else {
    return {
      type: SchemaType[property.type.toUpperCase()],
    };
  }
}

function toGeminiTool(
  tool: z.infer<typeof ToolDefinitionSchema>
): FunctionDeclaration {
  const declaration: FunctionDeclaration = {
    name: tool.name.replace(/\//g, '__'), // Gemini throws on '/' in tool name
    description: tool.description,
    parameters: convertSchemaProperty(tool.inputSchema),
  };
  return declaration;
}

function toInlineData(part: MediaPart): InlineDataPart {
  const dataUrl = part.media.url;
  const b64Data = dataUrl.substring(dataUrl.indexOf(',')! + 1);
  const contentType =
    part.media.contentType ||
    dataUrl.substring(dataUrl.indexOf(':')! + 1, dataUrl.indexOf(';'));
  return { inlineData: { mimeType: contentType, data: b64Data } };
}

function toFileData(part: MediaPart): FileDataPart {
  if (!part.media.contentType)
    throw new Error(
      'Must supply a `contentType` when sending File URIs to Gemini.'
    );
  return {
    fileData: { mimeType: part.media.contentType, fileUri: part.media.url },
  };
}

function fromInlineData(inlinePart: InlineDataPart): MediaPart {
  // Check if the required properties exist
  if (
    !inlinePart.inlineData ||
    !inlinePart.inlineData.hasOwnProperty('mimeType') ||
    !inlinePart.inlineData.hasOwnProperty('data')
  ) {
    throw new Error('Invalid InlineDataPart: missing required properties');
  }
  const { mimeType, data } = inlinePart.inlineData;
  // Combine data and mimeType into a data URL
  const dataUrl = `data:${mimeType};base64,${data}`;
  return {
    media: {
      url: dataUrl,
      contentType: mimeType,
    },
  };
}

function toFunctionCall(part: ToolRequestPart): FunctionCallPart {
  if (!part?.toolRequest?.input) {
    throw Error('Invalid ToolRequestPart: input was missing.');
  }
  return {
    functionCall: {
      name: part.toolRequest.name,
      args: part.toolRequest.input,
    },
  };
}

function fromFunctionCall(part: FunctionCallPart): ToolRequestPart {
  if (!part.functionCall) {
    throw Error('Invalid FunctionCallPart');
  }
  return {
    toolRequest: {
      name: part.functionCall.name,
      input: part.functionCall.args,
    },
  };
}

function toFunctionResponse(part: ToolResponsePart): FunctionResponsePart {
  if (!part?.toolResponse?.output) {
    throw Error('Invalid ToolResponsePart: output was missing.');
  }
  return {
    functionResponse: {
      name: part.toolResponse.name,
      response: {
        name: part.toolResponse.name,
        content: part.toolResponse.output,
      },
    },
  };
}

function fromFunctionResponse(part: FunctionResponsePart): ToolResponsePart {
  if (!part.functionResponse) {
    throw new Error('Invalid FunctionResponsePart.');
  }
  return {
    toolResponse: {
      name: part.functionResponse.name.replace(/__/g, '/'), // restore slashes
      output: part.functionResponse.response,
    },
  };
}

function fromExecutableCode(part: GeminiPart): Part {
  if (!part.executableCode) {
    throw new Error('Invalid GeminiPart: missing executableCode');
  }
  return {
    custom: {
      executableCode: {
        language: part.executableCode.language,
        code: part.executableCode.code,
      },
    },
  };
}

function fromCodeExecutionResult(part: GeminiPart): Part {
  if (!part.codeExecutionResult) {
    throw new Error('Invalid GeminiPart: missing codeExecutionResult');
  }
  return {
    custom: {
      codeExecutionResult: {
        outcome: part.codeExecutionResult.outcome,
        output: part.codeExecutionResult.output,
      },
    },
  };
}

function toCustomPart(part: Part): GeminiPart {
  if (!part.custom) {
    throw new Error('Invalid GeminiPart: missing custom');
  }
  if (part.custom.codeExecutionResult) {
    return { codeExecutionResult: part.custom.codeExecutionResult };
  }
  if (part.custom.executableCode) {
    return { executableCode: part.custom.executableCode };
  }
  throw new Error('Unsupported Custom Part type');
}

function toGeminiPart(part: Part): GeminiPart {
  if (part.text !== undefined) return { text: part.text || ' ' };
  if (part.media) {
    if (part.media.url.startsWith('data:')) return toInlineData(part);
    return toFileData(part);
  }
  if (part.toolRequest) return toFunctionCall(part);
  if (part.toolResponse) return toFunctionResponse(part);
  if (part.custom) return toCustomPart(part);
  throw new Error('Unsupported Part type' + JSON.stringify(part));
}

function fromGeminiPart(part: GeminiPart, jsonMode: boolean): Part {
  // if (jsonMode && part.text !== undefined) {
  //   return { data: JSON.parse(part.text) };
  // }
  if (part.text !== undefined) return { text: part.text };
  if (part.inlineData) return fromInlineData(part);
  if (part.functionCall) return fromFunctionCall(part);
  if (part.functionResponse) return fromFunctionResponse(part);
  if (part.executableCode) return fromExecutableCode(part);
  if (part.codeExecutionResult) return fromCodeExecutionResult(part);
  throw new Error('Unsupported GeminiPart type');
}

export function toGeminiMessage(
  message: MessageData,
  model?: ModelReference<z.ZodTypeAny>
): GeminiMessage {
  return {
    role: toGeminiRole(message.role, model),
    parts: message.content.map(toGeminiPart),
  };
}

export function toGeminiSystemInstruction(message: MessageData): GeminiMessage {
  return {
    role: 'user',
    parts: message.content.map(toGeminiPart),
  };
}

function fromGeminiFinishReason(
  reason: GeminiCandidate['finishReason']
): CandidateData['finishReason'] {
  if (!reason) return 'unknown';
  switch (reason) {
    case 'STOP':
      return 'stop';
    case 'MAX_TOKENS':
      return 'length';
    case 'SAFETY': // blocked for safety
    case 'RECITATION': // blocked for reciting training data
      return 'blocked';
    default:
      return 'unknown';
  }
}

export function fromGeminiCandidate(
  candidate: GeminiCandidate,
  jsonMode: boolean = false
): CandidateData {
  return {
    index: candidate.index || 0, // reasonable default?
    message: {
      role: 'model',
      content: (candidate.content?.parts || []).map((part) =>
        fromGeminiPart(part, jsonMode)
      ),
    },
    finishReason: fromGeminiFinishReason(candidate.finishReason),
    finishMessage: candidate.finishMessage,
    custom: {
      safetyRatings: candidate.safetyRatings,
      citationMetadata: candidate.citationMetadata,
    },
  };
}

export function cleanSchema(schema: JSONSchema): JSONSchema {
  const out = structuredClone(schema);
  for (const key in out) {
    if (key === '$schema' || key === 'additionalProperties') {
      delete out[key];
      continue;
    }
    if (typeof out[key] === 'object') {
      out[key] = cleanSchema(out[key]);
    }
    // Zod nullish() and picoschema optional fields will produce type `["string", "null"]`
    // which is not supported by the model API. Convert them to just `"string"`.
    if (key === 'type' && Array.isArray(out[key])) {
      // find the first that's not `null`.
      out[key] = out[key].find((t) => t !== 'null');
    }
  }
  return out;
}

/**
 * Defines a new GoogleAI model.
 */
export function defineGoogleAIModel(
  ai: Genkit,
  name: string,
  apiKey?: string,
  apiVersion?: string,
  baseUrl?: string,
  info?: ModelInfo,
  defaultConfig?: GeminiConfig
): ModelAction {
  if (!apiKey) {
    apiKey = process.env.GOOGLE_GENAI_API_KEY || process.env.GOOGLE_API_KEY;
  }
  if (!apiKey) {
    throw new Error(
      'Please pass in the API key or set the GOOGLE_GENAI_API_KEY or GOOGLE_API_KEY environment variable.\n' +
        'For more details see https://firebase.google.com/docs/genkit/plugins/google-genai'
    );
  }
  const apiModelName = name.startsWith('googleai/')
    ? name.substring('googleai/'.length)
    : name;

  const model: ModelReference<z.ZodTypeAny> =
    SUPPORTED_GEMINI_MODELS[name] ??
    modelRef({
      name: `googleai/${apiModelName}`,
      info: {
        label: `Google AI - ${apiModelName}`,
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
  if (SUPPORTED_V1_MODELS[name]) {
    middleware.push(simulateSystemPrompt());
  }
  if (model.info?.supports?.media) {
    // the gemini api doesn't support downloading media from http(s)
    middleware.push(
      downloadRequestMedia({
        maxBytes: 1024 * 1024 * 10,
        // don't downlaod files that have been uploaded using the Files API
        filter: (part) =>
          !part.media.url.startsWith(
            'https://generativelanguage.googleapis.com/'
          ),
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
      const options: RequestOptions = { apiClient: GENKIT_CLIENT_HEADER };
      if (apiVersion) {
        options.apiVersion = apiVersion;
      }
      if (apiVersion) {
        options.baseUrl = baseUrl;
      }
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
      if (SUPPORTED_V15_MODELS[name]) {
        const systemMessage = messages.find((m) => m.role === 'system');
        if (systemMessage) {
          messages.splice(messages.indexOf(systemMessage), 1);
          systemInstruction = toGeminiSystemInstruction(systemMessage);
        }
      }

      const tools: Tool[] = [];
      if (request.tools?.length) {
        tools.push({
          functionDeclarations: request.tools.map(toGeminiTool),
        });
      }

      if (requestConfig.codeExecution) {
        tools.push({
          codeExecution:
            request.config.codeExecution === true
              ? {}
              : request.config.codeExecution,
        });
      }

      let toolConfig: ToolConfig | undefined;
      if (requestConfig.functionCallingConfig) {
        toolConfig = {
          functionCallingConfig: {
            allowedFunctionNames:
              requestConfig.functionCallingConfig.allowedFunctionNames,
            mode: toFunctionModeEnum(requestConfig.functionCallingConfig.mode),
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
        candidateCount: request.candidates || undefined,
        temperature: requestConfig.temperature,
        maxOutputTokens: requestConfig.maxOutputTokens,
        topK: requestConfig.topK,
        topP: requestConfig.topP,
        stopSequences: requestConfig.stopSequences,
        responseMimeType: jsonMode ? 'application/json' : undefined,
      };

      if (request.output?.constrained && jsonMode) {
        generationConfig.responseSchema = cleanSchema(request.output.schema);
      }

      const msg = toGeminiMessage(messages[messages.length - 1], model);

      const fromJSONModeScopedGeminiCandidate = (
        candidate: GeminiCandidate
      ) => {
        return fromGeminiCandidate(candidate, jsonMode);
      };

      let chatRequest: StartChatParams = {
        systemInstruction,
        generationConfig,
        tools: tools.length ? tools : undefined,
        toolConfig,
        history: messages
          .slice(0, -1)
          .map((message) => toGeminiMessage(message, model)),
        safetySettings: requestConfig.safetySettings,
      } as StartChatParams;
      const modelVersion = (request.config?.version ||
        model.version ||
        name) as string;
      const cacheConfigDetails = extractCacheConfig(request);

      const { chatRequest: updatedChatRequest, cache } =
        await handleCacheIfNeeded(
          apiKey!,
          request,
          chatRequest,
          modelVersion,
          cacheConfigDetails
        );

      const client = new GoogleGenerativeAI(apiKey!);
      let genModel: GenerativeModel;

      if (cache) {
        genModel = client.getGenerativeModelFromCachedContent(
          cache,
          {
            model: modelVersion,
          },
          options
        );
      } else {
        genModel = client.getGenerativeModel(
          {
            model: modelVersion,
          },
          options
        );
      }

      if (sendChunk) {
        const result = await genModel
          .startChat(updatedChatRequest)
          .sendMessageStream(msg.parts, options);
        for await (const item of result.stream) {
          (item as GenerateContentResponse).candidates?.forEach((candidate) => {
            const c = fromJSONModeScopedGeminiCandidate(candidate);
            sendChunk({
              index: c.index,
              content: c.message.content,
            });
          });
        }
        const response = await result.response;
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
        return {
          candidates: candidates.map(fromJSONModeScopedGeminiCandidate) || [],
          custom: response,
        };
      } else {
        const result = await genModel
          .startChat(updatedChatRequest)
          .sendMessage(msg.parts, options);
        if (!result.response.candidates?.length)
          throw new Error('No valid candidates returned.');
        const responseCandidates =
          result.response.candidates.map(fromJSONModeScopedGeminiCandidate) ||
          [];
        return {
          candidates: responseCandidates,
          custom: result.response,
          usage: {
            ...getBasicUsageStats(request.messages, responseCandidates),
            inputTokens: result.response.usageMetadata?.promptTokenCount,
            outputTokens: result.response.usageMetadata?.candidatesTokenCount,
            totalTokens: result.response.usageMetadata?.totalTokenCount,
          },
        };
      }
    }
  );
}

/** Converts mode from the config, which follows Gemini naming convention. */
function toFunctionModeEnum(
  configEnum: string | undefined
): FunctionCallingMode | undefined {
  if (configEnum === undefined) {
    return undefined;
  }
  switch (configEnum) {
    case 'MODE_UNSPECIFIED': {
      return FunctionCallingMode.MODE_UNSPECIFIED;
    }
    case 'ANY': {
      return FunctionCallingMode.ANY;
    }
    case 'AUTO': {
      return FunctionCallingMode.AUTO;
    }
    case 'NONE': {
      return FunctionCallingMode.NONE;
    }
    default:
      throw new Error(`unsupported function calling mode: ${configEnum}`);
  }
}

/** Converts mode from genkit tool choice. */
function toGeminiFunctionModeEnum(
  genkitMode: 'auto' | 'required' | 'none'
): FunctionCallingMode | undefined {
  if (genkitMode === undefined) {
    return undefined;
  }
  switch (genkitMode) {
    case 'required': {
      return FunctionCallingMode.ANY;
    }
    case 'auto': {
      return FunctionCallingMode.AUTO;
    }
    case 'none': {
      return FunctionCallingMode.NONE;
    }
    default:
      throw new Error(`unsupported function calling mode: ${genkitMode}`);
  }
}
