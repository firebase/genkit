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

import { GenkitError, z } from 'genkit';
import {
  CandidateData,
  MessageData,
  ModelReference,
  Part,
  ToolDefinition,
} from 'genkit/model';
import {
  FunctionCallingMode,
  FunctionDeclaration,
  GenerateContentCandidate as GeminiCandidate,
  Content as GeminiContent,
  Part as GeminiPart,
  Schema,
  SchemaType,
} from './types.js';

export function toGeminiTool(tool: ToolDefinition): FunctionDeclaration {
  const declaration: FunctionDeclaration = {
    name: tool.name.replace(/\//g, '__'), // Gemini throws on '/' in tool name
    description: tool.description,
    parameters: toGeminiSchemaProperty(tool.inputSchema),
  };
  return declaration;
}

function toGeminiSchemaProperty(property?: ToolDefinition['inputSchema']) {
  if (!property || !property.type) {
    return undefined;
  }
  const baseSchema: Schema = {};
  if (property.description) {
    baseSchema.description = property.description;
  }
  if (property.enum) {
    baseSchema.enum = property.enum;
  }
  if (property.nullable) {
    baseSchema.nullable = property.nullable;
  }
  let propertyType;
  // nullable schema can ALSO be defined as, for example, type=['string','null']
  if (Array.isArray(property.type)) {
    const types = property.type as string[];
    if (types.includes('null')) {
      baseSchema.nullable = true;
    }
    // grab the type that's not `null`
    propertyType = types.find((t) => t !== 'null');
  } else {
    propertyType = property.type;
  }
  if (propertyType === 'object') {
    const nestedProperties = {};
    Object.keys(property.properties).forEach((key) => {
      nestedProperties[key] = toGeminiSchemaProperty(property.properties[key]);
    });
    return {
      ...baseSchema,
      type: SchemaType.OBJECT,
      properties: nestedProperties,
      required: property.required,
    };
  } else if (propertyType === 'array') {
    return {
      ...baseSchema,
      type: SchemaType.ARRAY,
      items: toGeminiSchemaProperty(property.items),
    };
  } else {
    const schemaType = SchemaType[propertyType.toUpperCase()] as SchemaType;
    if (!schemaType) {
      throw new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: `Unsupported property type ${propertyType.toUpperCase()}`,
      });
    }
    return {
      ...baseSchema,
      type: schemaType,
    };
  }
}

function toGeminiMedia(part: Part): GeminiPart {
  if (part.media?.url.startsWith('data:')) {
    // Inline data
    const dataUrl = part.media.url;
    const b64Data = dataUrl.substring(dataUrl.indexOf(',')! + 1);
    const contentType =
      part.media.contentType ||
      dataUrl.substring(dataUrl.indexOf(':')! + 1, dataUrl.indexOf(';'));
    return { inlineData: { mimeType: contentType, data: b64Data } };
  }

  // File data
  if (!part.media?.contentType) {
    throw Error(
      'Must supply a `contentType` when sending File URIs to Gemini.'
    );
  }
  return {
    fileData: {
      mimeType: part.media.contentType,
      fileUri: part.media.url,
    },
  };
}

function toGeminiToolRequest(part: Part): GeminiPart {
  if (!part.toolRequest?.input) {
    throw Error('Invalid ToolRequestPart: input was missing.');
  }
  return {
    functionCall: {
      name: part.toolRequest.name,
      args: part.toolRequest.input,
    },
  };
}

function toGeminiToolResponse(part: Part): GeminiPart {
  if (!part.toolResponse?.output) {
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

function toGeminiReasoning(part: Part): GeminiPart {
  const out: GeminiPart = { thought: true };
  if (typeof part.metadata?.thoughtSignature === 'string') {
    out.thoughtSignature = part.metadata.thoughtSignature;
  }
  if (part.reasoning?.length) {
    out.text = part.reasoning;
  }
  return out;
}

function toGeminiCustom(part: Part): GeminiPart {
  if (part.custom?.codeExecutionResult) {
    return {
      codeExecutionResult: part.custom.codeExecutionResult,
    };
  }
  if (part.custom?.executableCode) {
    return {
      executableCode: part.custom.executableCode,
    };
  }
  throw new Error('Unsupported Custom Part type');
}

function toGeminiPart(part: Part): GeminiPart {
  if (part.text) {
    return { text: part.text };
  }
  if (part.media) {
    return toGeminiMedia(part);
  }
  if (part.toolRequest) {
    return toGeminiToolRequest(part);
  }
  if (part.toolResponse) {
    return toGeminiToolResponse(part);
  }
  if (typeof part.reasoning === 'string') {
    return toGeminiReasoning(part);
  }
  if (part.custom) {
    return toGeminiCustom(part);
  }
  throw new Error('Unsupported Part type ' + JSON.stringify(part));
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
      if (model?.info?.supports?.systemRole) {
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

export function toGeminiMessage(
  message: MessageData,
  model?: ModelReference<z.ZodTypeAny>
): GeminiContent {
  let sortedParts = message.content;
  if (message.role === 'tool') {
    sortedParts = [...message.content].sort((a, b) => {
      const aRef = a.toolResponse?.ref;
      const bRef = b.toolResponse?.ref;
      if (!aRef && !bRef) return 0;
      if (!aRef) return 1;
      if (!bRef) return -1;
      return parseInt(aRef, 10) - parseInt(bRef, 10);
    });
  }
  return {
    role: toGeminiRole(message.role, model),
    parts: sortedParts.map(toGeminiPart),
  };
}

export function toGeminiSystemInstruction(message: MessageData): GeminiContent {
  return {
    role: 'user',
    parts: message.content.map(toGeminiPart),
  };
}

/**
 * Converts mode from either genkit tool choice (lowercase)
 * or functionCallingConfig (uppercase).
 * @param from The mode to convert from
 * @returns
 */
export function toGeminiFunctionModeEnum(
  from?: string
  //genkitMode: 'auto' | 'required' | 'none'
): FunctionCallingMode | undefined {
  if (from === undefined) {
    return undefined;
  }
  switch (from) {
    case 'MODE_UNSPECIFIED': {
      return FunctionCallingMode.MODE_UNSPECIFIED;
    }
    case 'required':
    case 'ANY': {
      return FunctionCallingMode.ANY;
    }
    case 'auto':
    case 'AUTO': {
      return FunctionCallingMode.AUTO;
    }
    case 'none':
    case 'NONE': {
      return FunctionCallingMode.NONE;
    }
    default:
      throw new Error(`unsupported function calling mode: ${from}`);
  }
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
    case 'LANGUAGE': // blocked for using an unsupported language
    case 'BLOCKLIST': // blocked for forbidden terms
    case 'PROHIBITED_CONTENT': // blocked for potentially containing prohibited content
    case 'SPII': // blocked for potentially containing Sensitive Personally Identifiable Information
      return 'blocked';
    case 'MALFORMED_FUNCTION_CALL':
    case 'OTHER':
      return 'other';
    default:
      return 'unknown';
  }
}

function fromGeminiThought(part: GeminiPart): Part {
  return {
    reasoning: part.text || '',
    metadata: { thoughtSignature: part.thoughtSignature },
  };
}

function fromGeminiInlineData(part: GeminiPart): Part {
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

function fromGeminiFileData(part: GeminiPart): Part {
  if (
    !part.fileData ||
    !part.fileData.hasOwnProperty('mimeType') ||
    !part.fileData.hasOwnProperty('fileUri')
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

function fromGeminiFunctionCall(part: GeminiPart, ref: string): Part {
  if (!part.functionCall) {
    throw Error(
      'Invalid Gemini Function Call Part: missing function call data'
    );
  }
  return {
    toolRequest: {
      name: part.functionCall.name,
      input: part.functionCall.args,
      ref,
    },
  };
}

function fromGeminiFunctionResponse(part: GeminiPart, ref?: string): Part {
  if (!part.functionResponse) {
    throw new Error(
      'Invalid Gemini Function Call Part: missing function call data'
    );
  }
  return {
    toolResponse: {
      name: part.functionResponse.name.replace(/__/g, '/'), // restore slashes
      output: part.functionResponse.response,
      ref,
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

function fromGeminiPart(part: GeminiPart, ref: string): Part {
  if (part.thought) return fromGeminiThought(part as any);
  if (typeof part.text === 'string') return { text: part.text };
  if (part.inlineData) return fromGeminiInlineData(part);
  if (part.fileData) return fromGeminiFileData(part);
  if (part.functionCall) return fromGeminiFunctionCall(part, ref);
  if (part.functionResponse) return fromGeminiFunctionResponse(part, ref);
  if (part.executableCode) return fromExecutableCode(part);
  if (part.codeExecutionResult) return fromCodeExecutionResult(part);

  throw new Error('Unsupported GeminiPart type ' + JSON.stringify(part));
}

export function fromGeminiCandidate(candidate: GeminiCandidate): CandidateData {
  const parts = candidate.content?.parts || [];
  const genkitCandidate: CandidateData = {
    index: candidate.index || 0,
    message: {
      role: 'model',
      content: parts
        // the model sometimes returns empty parts, ignore those.
        .filter((p) => Object.keys(p).length > 0)
        .map((part, index) => fromGeminiPart(part, index.toString())),
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
