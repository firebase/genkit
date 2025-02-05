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
  Content,
  FunctionCallingMode,
  FunctionDeclaration,
  FunctionDeclarationSchemaType,
  Part as GeminiPart,
  GenerateContentCandidate,
  GenerateContentResponse,
  GenerativeModelPreview,
  HarmBlockThreshold,
  HarmCategory,
  StartChatParams,
  ToolConfig,
  VertexAI,
  type GoogleSearchRetrieval,
} from '@google-cloud/vertexai';
import { ApiClient } from '@google-cloud/vertexai/build/src/resources/index.js';
import { GENKIT_CLIENT_HEADER, Genkit, JSONSchema, z } from 'genkit';
import {
  CandidateData,
  GenerateRequest,
  GenerationCommonConfigSchema,
  MediaPart,
  MessageData,
  ModelAction,
  ModelInfo,
  ModelMiddleware,
  ModelReference,
  Part,
  ToolDefinitionSchema,
  getBasicUsageStats,
  modelRef,
} from 'genkit/model';
import {
  downloadRequestMedia,
  simulateSystemPrompt,
} from 'genkit/model/middleware';
import { GoogleAuth } from 'google-auth-library';
import { PluginOptions } from './common/types.js';
import { handleCacheIfNeeded } from './context-caching/index.js';
import { extractCacheConfig } from './context-caching/utils.js';

const SafetySettingsSchema = z.object({
  category: z.nativeEnum(HarmCategory),
  threshold: z.nativeEnum(HarmBlockThreshold),
});

const VertexRetrievalSchema = z.object({
  datastore: z.object({
    projectId: z.string().optional(),
    location: z.string().optional(),
    dataStoreId: z.string(),
  }),
  disableAttribution: z.boolean().optional(),
});

const GoogleSearchRetrievalSchema = z.object({
  disableAttribution: z.boolean().optional(),
});

/**
 * Zod schema of Gemini model options.
 */
export const GeminiConfigSchema = GenerationCommonConfigSchema.extend({
  /**
   * GCP region (e.g. us-central1)
   */
  location: z.string().describe('banana').optional(),

  /**
   * Safety filter settings. See: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/configure-safety-filters#configurable-filters
   *
   * E.g.
   *
   * ```js
   * config: {
   *   safetySettings: [
   *     {
   *       category: 'HARM_CATEGORY_HATE_SPEECH',
   *       threshold: 'BLOCK_LOW_AND_ABOVE',
   *     },
   *     {
   *       category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
   *       threshold: 'BLOCK_MEDIUM_AND_ABOVE',
   *     },
   *     {
   *       category: 'HARM_CATEGORY_HARASSMENT',
   *       threshold: 'BLOCK_ONLY_HIGH',
   *     },
   *     {
   *       category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
   *       threshold: 'BLOCK_NONE',
   *     },
   *   ],
   * }
   * ```
   */
  safetySettings: z.array(SafetySettingsSchema).optional(),

  /**
   * Vertex retrieval options.
   *
   * E.g.
   *
   * ```js
   *   config: {
   *     vertexRetrieval: {
   *       datastore: {
   *         projectId: 'your-cloud-project',
   *         location: 'us-central1',
   *         collection: 'your-collection',
   *       },
   *       disableAttribution: true,
   *     }
   *   }
   * ```
   */
  vertexRetrieval: VertexRetrievalSchema.optional(),

  /**
   * Google Search retrieval options.
   *
   * ```js
   *   config: {
   *     googleSearchRetrieval: {
   *       disableAttribution: true,
   *     }
   *   }
   * ```
   */
  googleSearchRetrieval: GoogleSearchRetrievalSchema.optional(),

  /**
   * Function calling options.
   *
   * E.g. forced tool call:
   *
   * ```js
   *   config: {
   *     functionCallingConfig: {
   *       mode: 'ANY',
   *     }
   *   }
   * ```
   */
  functionCallingConfig: z
    .object({
      mode: z.enum(['MODE_UNSPECIFIED', 'AUTO', 'ANY', 'NONE']).optional(),
      allowedFunctionNames: z.array(z.string()).optional(),
    })
    .optional(),
});

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
    name: `vertexai/${version}`,
    config: options,
    configSchema: GeminiConfigSchema,
    info: {
      ...nearestModel.info,
      // If exact suffix match for a known model, use its label, otherwise create a new label
      label: nearestModel.name.endsWith(version)
        ? nearestModel.info?.label
        : `Vertex AI - ${version}`,
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
 * Gemini model configuration options.
 *
 * E.g.
 * ```js
 *   config: {
 *     temperature: 0.9,
 *     maxOutputTokens: 300,
 *     safetySettings: [
 *       {
 *         category: 'HARM_CATEGORY_HATE_SPEECH',
 *         threshold: 'BLOCK_LOW_AND_ABOVE',
 *       },
 *       {
 *         category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
 *         threshold: 'BLOCK_MEDIUM_AND_ABOVE',
 *       },
 *       {
 *         category: 'HARM_CATEGORY_HARASSMENT',
 *         threshold: 'BLOCK_ONLY_HIGH',
 *       },
 *       {
 *         category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
 *         threshold: 'BLOCK_NONE',
 *       },
 *     ],
 *     functionCallingConfig: {
 *       mode: 'ANY',
 *     }
 *   }
 * ```
 */
export type GeminiConfig = z.infer<typeof GeminiConfigSchema>;

export const gemini10Pro = modelRef({
  name: 'vertexai/gemini-1.0-pro',
  info: {
    label: 'Vertex AI - Gemini Pro',
    versions: ['gemini-1.0-pro-001', 'gemini-1.0-pro-002'],
    supports: {
      multiturn: true,
      media: false,
      tools: true,
      systemRole: true,
      constrained: 'no-tools',
      toolChoice: true,
    },
  },
  configSchema: GeminiConfigSchema,
});

export const gemini15Pro = modelRef({
  name: 'vertexai/gemini-1.5-pro',
  info: {
    label: 'Vertex AI - Gemini 1.5 Pro',
    versions: ['gemini-1.5-pro-001', 'gemini-1.5-pro-002'],
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

export const gemini15Flash = modelRef({
  name: 'vertexai/gemini-1.5-flash',
  info: {
    label: 'Vertex AI - Gemini 1.5 Flash',
    versions: ['gemini-1.5-flash-001', 'gemini-1.5-flash-002'],
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

export const gemini20Flash001 = modelRef({
  name: 'vertexai/gemini-2.0-flash-001',
  info: {
    label: 'Vertex AI - Gemini 2.0 Flash 001',
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

export const gemini20FlashLitePreview0205 = modelRef({
  name: 'vertexai/gemini-2.0-flash-lite-preview-02-05',
  info: {
    label: 'Vertex AI - Gemini 2.0 Flash Lite Preview 02-05',
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

export const gemini20ProExp0205 = modelRef({
  name: 'vertexai/gemini-2.0-pro-exp-02-05',
  info: {
    label: 'Vertex AI - Gemini 2.0 Flash Pro Experimental 02-05',
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

export const GENERIC_GEMINI_MODEL = modelRef({
  name: 'vertexai/gemini',
  configSchema: GeminiConfigSchema,
  info: {
    label: 'Google Gemini',
    supports: {
      multiturn: true,
      media: true,
      tools: true,
      toolChoice: true,
      systemRole: true,
    },
  },
});

export const SUPPORTED_V1_MODELS = {
  'gemini-1.0-pro': gemini10Pro,
};

export const SUPPORTED_V15_MODELS = {
  'gemini-1.5-pro': gemini15Pro,
  'gemini-1.5-flash': gemini15Flash,
  'gemini-2.0-flash-001': gemini20Flash001,
  'gemini-2.0-flash-lite-preview-02-05': gemini20FlashLitePreview0205,
  'gemini-2.0-pro-exp-02-05': gemini20ProExp0205,
};

export const SUPPORTED_GEMINI_MODELS = {
  ...SUPPORTED_V1_MODELS,
  ...SUPPORTED_V15_MODELS,
} as const;

function toGeminiRole(
  role: MessageData['role'],
  modelInfo?: ModelInfo
): string {
  switch (role) {
    case 'user':
      return 'user';
    case 'model':
      return 'model';
    case 'system':
      if (modelInfo && modelInfo.supports?.systemRole) {
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

const toGeminiTool = (
  tool: z.infer<typeof ToolDefinitionSchema>
): FunctionDeclaration => {
  const declaration: FunctionDeclaration = {
    name: tool.name.replace(/\//g, '__'), // Gemini throws on '/' in tool name
    description: tool.description,
    parameters: convertSchemaProperty(tool.inputSchema),
  };
  return declaration;
};

const toGeminiFileDataPart = (part: MediaPart): GeminiPart => {
  const media = part.media;
  if (media.url.startsWith('gs://') || media.url.startsWith('http')) {
    if (!media.contentType)
      throw new Error(
        'Must supply contentType when using media from http(s):// or gs:// URLs.'
      );
    return {
      fileData: {
        mimeType: media.contentType,
        fileUri: media.url,
      },
    };
  } else if (media.url.startsWith('data:')) {
    const dataUrl = media.url;
    const b64Data = dataUrl.substring(dataUrl.indexOf(',')! + 1);
    const contentType =
      media.contentType ||
      dataUrl.substring(dataUrl.indexOf(':')! + 1, dataUrl.indexOf(';'));
    return { inlineData: { mimeType: contentType, data: b64Data } };
  }

  throw Error(
    'Could not convert genkit part to gemini tool response part: missing file data'
  );
};

const toGeminiToolRequestPart = (part: Part): GeminiPart => {
  if (!part?.toolRequest?.input) {
    throw Error(
      'Could not convert genkit part to gemini tool response part: missing tool request data'
    );
  }
  return {
    functionCall: {
      name: part.toolRequest.name,
      args: part.toolRequest.input,
    },
  };
};

const toGeminiToolResponsePart = (part: Part): GeminiPart => {
  if (!part?.toolResponse?.output) {
    throw Error(
      'Could not convert genkit part to gemini tool response part: missing tool response data'
    );
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
};

export function toGeminiSystemInstruction(message: MessageData): Content {
  return {
    role: 'user',
    parts: message.content.map(toGeminiPart),
  };
}

export function toGeminiMessage(
  message: MessageData,
  modelInfo?: ModelInfo
): Content {
  return {
    role: toGeminiRole(message.role, modelInfo),
    parts: message.content.map(toGeminiPart),
  };
}

function fromGeminiFinishReason(
  reason: GenerateContentCandidate['finishReason']
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

function toGeminiPart(part: Part): GeminiPart {
  if (part.text) {
    return { text: part.text };
  } else if (part.media) {
    return toGeminiFileDataPart(part);
  } else if (part.toolRequest) {
    return toGeminiToolRequestPart(part);
  } else if (part.toolResponse) {
    return toGeminiToolResponsePart(part);
  } else {
    throw new Error('unsupported type');
  }
}

function fromGeminiInlineDataPart(part: GeminiPart): MediaPart {
  // Check if the required properties exist
  if (
    !part.inlineData ||
    !part.inlineData.hasOwnProperty('mimeType') ||
    !part.inlineData.hasOwnProperty('data')
  ) {
    throw new Error('Invalid GeminiPart: missing required properties');
  }
  const { mimeType, data } = part.inlineData;
  // Combine data and mimeType into a data URL
  const dataUrl = `data:${mimeType};base64,${data}`;
  return {
    media: {
      url: dataUrl,
      contentType: mimeType,
    },
  };
}

function fromGeminiFileDataPart(part: GeminiPart): MediaPart {
  if (
    !part.fileData ||
    !part.fileData.hasOwnProperty('mimeType') ||
    !part.fileData.hasOwnProperty('url')
  ) {
    throw new Error(
      'Invalid Gemini File Data Part: missing required properties'
    );
  }

  return {
    media: {
      url: part.fileData?.fileUri,
      contentType: part.fileData?.mimeType,
    },
  };
}

function fromGeminiFunctionCallPart(part: GeminiPart): Part {
  if (!part.functionCall) {
    throw new Error(
      'Invalid Gemini Function Call Part: missing function call data'
    );
  }
  return {
    toolRequest: {
      name: part.functionCall.name,
      input: part.functionCall.args,
    },
  };
}

function fromGeminiFunctionResponsePart(part: GeminiPart): Part {
  if (!part.functionResponse) {
    throw new Error(
      'Invalid Gemini Function Call Part: missing function call data'
    );
  }
  return {
    toolResponse: {
      name: part.functionResponse.name.replace(/__/g, '/'), // restore slashes
      output: part.functionResponse.response,
    },
  };
}

// Converts vertex part to genkit part
function fromGeminiPart(part: GeminiPart, jsonMode: boolean): Part {
  // if (jsonMode && part.text !== undefined) {
  //   return { data: JSON.parse(part.text) };
  // }
  if (part.text !== undefined) return { text: part.text };
  if (part.functionCall) return fromGeminiFunctionCallPart(part);
  if (part.functionResponse) return fromGeminiFunctionResponsePart(part);
  if (part.inlineData) return fromGeminiInlineDataPart(part);
  if (part.fileData) return fromGeminiFileDataPart(part);
  throw new Error(
    'Part type is unsupported/corrupted. Either data is missing or type cannot be inferred from type.'
  );
}

export function fromGeminiCandidate(
  candidate: GenerateContentCandidate,
  jsonMode: boolean
): CandidateData {
  const parts = candidate.content.parts || [];
  const genkitCandidate: CandidateData = {
    index: candidate.index || 0, // reasonable default?
    message: {
      role: 'model',
      content: parts.map((p) => fromGeminiPart(p, jsonMode)),
    },
    finishReason: fromGeminiFinishReason(candidate.finishReason),
    finishMessage: candidate.finishMessage,
    custom: {
      safetyRatings: candidate.safetyRatings,
      citationMetadata: candidate.citationMetadata,
    },
  };
  return genkitCandidate;
}

// Translate JSON schema to Vertex AI's format. Specifically, the type field needs be mapped.
// Since JSON schemas can include nested arrays/objects, we have to recursively map the type field
// in all nested fields.
const convertSchemaProperty = (property) => {
  if (!property || !property.type) {
    return null;
  }
  if (property.type === 'object') {
    const nestedProperties = {};
    Object.keys(property.properties).forEach((key) => {
      nestedProperties[key] = convertSchemaProperty(property.properties[key]);
    });
    return {
      type: FunctionDeclarationSchemaType.OBJECT,
      properties: nestedProperties,
      required: property.required,
    };
  } else if (property.type === 'array') {
    return {
      type: FunctionDeclarationSchemaType.ARRAY,
      items: convertSchemaProperty(property.items),
    };
  } else {
    return {
      type: FunctionDeclarationSchemaType[property.type.toUpperCase()],
    };
  }
};

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
 * Define a Vertex AI Gemini model.
 */
export function defineGeminiKnownModel(
  ai: Genkit,
  name: string,
  vertexClientFactory: (
    request: GenerateRequest<typeof GeminiConfigSchema>
  ) => VertexAI,
  options: PluginOptions
): ModelAction {
  const modelName = `vertexai/${name}`;

  const model: ModelReference<z.ZodTypeAny> = SUPPORTED_GEMINI_MODELS[name];
  if (!model) throw new Error(`Unsupported model: ${name}`);

  return defineGeminiModel(
    ai,
    modelName,
    name,
    model?.info,
    vertexClientFactory,
    options
  );
}

/**
 * Define a Vertex AI Gemini model.
 */
export function defineGeminiModel(
  ai: Genkit,
  modelName: string,
  version: string,
  modelInfo: ModelInfo | undefined,
  vertexClientFactory: (
    request: GenerateRequest<typeof GeminiConfigSchema>
  ) => VertexAI,
  options: PluginOptions
): ModelAction {
  const middlewares: ModelMiddleware[] = [];
  if (SUPPORTED_V1_MODELS[version]) {
    middlewares.push(simulateSystemPrompt());
  }
  if (modelInfo?.supports?.media) {
    // the gemini api doesn't support downloading media from http(s)
    middlewares.push(downloadRequestMedia({ maxBytes: 1024 * 1024 * 20 }));
  }

  return ai.defineModel(
    {
      name: modelName,
      ...modelInfo,
      configSchema: GeminiConfigSchema,
      use: middlewares,
    },
    async (request, streamingCallback) => {
      const vertex = vertexClientFactory(request);

      // Make a copy of messages to avoid side-effects
      const messages = [...request.messages];
      if (messages.length === 0) throw new Error('No messages provided.');

      // Handle system instructions separately
      let systemInstruction: Content | undefined = undefined;
      if (!SUPPORTED_V1_MODELS[version]) {
        const systemMessage = messages.find((m) => m.role === 'system');
        if (systemMessage) {
          messages.splice(messages.indexOf(systemMessage), 1);
          systemInstruction = toGeminiSystemInstruction(systemMessage);
        }
      }

      const tools = request.tools?.length
        ? [{ functionDeclarations: request.tools.map(toGeminiTool) }]
        : [];

      let toolConfig: ToolConfig | undefined;
      if (request?.config?.functionCallingConfig) {
        toolConfig = {
          functionCallingConfig: {
            allowedFunctionNames:
              request.config.functionCallingConfig.allowedFunctionNames,
            mode: toFunctionModeEnum(request.config.functionCallingConfig.mode),
          },
        };
      } else if (request.toolChoice) {
        toolConfig = {
          functionCallingConfig: {
            mode: toGeminiFunctionModeEnum(request.toolChoice),
          },
        };
      }

      // Cannot use tools and function calling at the same time
      const jsonMode =
        (request.output?.format === 'json' || !!request.output?.schema) &&
        tools.length === 0;

      let chatRequest: StartChatParams = {
        systemInstruction,
        tools,
        toolConfig,
        history: messages
          .slice(0, -1)
          .map((message) => toGeminiMessage(message, modelInfo)),
        generationConfig: {
          candidateCount: request.candidates || undefined,
          temperature: request.config?.temperature,
          maxOutputTokens: request.config?.maxOutputTokens,
          topK: request.config?.topK,
          topP: request.config?.topP,
          responseMimeType: jsonMode ? 'application/json' : undefined,
          stopSequences: request.config?.stopSequences,
        },
        safetySettings: request.config?.safetySettings,
      };

      // Handle cache
      const modelVersion = (request.config?.version || version) as string;
      const cacheConfigDetails = extractCacheConfig(request);

      const apiClient = new ApiClient(
        options.projectId!,
        options.location,
        'v1beta1',
        new GoogleAuth(options.googleAuth!)
      );

      const { chatRequest: updatedChatRequest, cache } =
        await handleCacheIfNeeded(
          apiClient,
          request,
          chatRequest,
          modelVersion,
          cacheConfigDetails
        );

      let genModel: GenerativeModelPreview;

      if (jsonMode && request.output?.constrained) {
        updatedChatRequest.generationConfig!.responseSchema = cleanSchema(
          request.output.schema
        );
      }

      if (request.config?.googleSearchRetrieval) {
        updatedChatRequest.tools?.push({
          googleSearchRetrieval: request.config
            .googleSearchRetrieval as GoogleSearchRetrieval,
        });
      }

      if (request.config?.vertexRetrieval) {
        const vertexRetrieval = request.config.vertexRetrieval;
        const _projectId =
          vertexRetrieval.datastore.projectId || options.projectId;
        const _location =
          vertexRetrieval.datastore.location || options.location;
        const _dataStoreId = vertexRetrieval.datastore.dataStoreId;
        const datastore = `projects/${_projectId}/locations/${_location}/collections/default_collection/dataStores/${_dataStoreId}`;
        updatedChatRequest.tools?.push({
          retrieval: {
            vertexAiSearch: {
              datastore,
            },
            disableAttribution: vertexRetrieval.disableAttribution,
          },
        });
      }

      const msg = toGeminiMessage(messages[messages.length - 1], modelInfo);

      if (cache) {
        genModel = vertex.preview.getGenerativeModelFromCachedContent(
          cache,
          {
            model: modelVersion,
          },
          {
            apiClient: GENKIT_CLIENT_HEADER,
          }
        );
      } else {
        genModel = vertex.preview.getGenerativeModel(
          {
            model: modelVersion,
          },
          {
            apiClient: GENKIT_CLIENT_HEADER,
          }
        );
      }

      // Handle streaming and non-streaming responses
      if (streamingCallback) {
        const result = await genModel
          .startChat(updatedChatRequest)
          .sendMessageStream(msg.parts);

        for await (const item of result.stream) {
          (item as GenerateContentResponse).candidates?.forEach((candidate) => {
            const c = fromGeminiCandidate(candidate, jsonMode);
            streamingCallback({
              index: c.index,
              content: c.message.content,
            });
          });
        }

        const response = await result.response;
        if (!response.candidates?.length) {
          throw new Error('No valid candidates returned.');
        }

        return {
          candidates: response.candidates.map((c) =>
            fromGeminiCandidate(c, jsonMode)
          ),
          custom: response,
        };
      } else {
        const result = await genModel
          .startChat(updatedChatRequest)
          .sendMessage(msg.parts);

        if (!result?.response.candidates?.length) {
          throw new Error('No valid candidates returned.');
        }

        const responseCandidates = result.response.candidates.map((c) =>
          fromGeminiCandidate(c, jsonMode)
        );

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
  enumMode: string | undefined
): FunctionCallingMode | undefined {
  if (enumMode === undefined) {
    return undefined;
  }
  switch (enumMode) {
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
      throw new Error(`unsupported function calling mode: ${enumMode}`);
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
