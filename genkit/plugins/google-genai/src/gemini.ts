import {
  CandidateData,
  MediaPart,
  MessageData,
  ModelAction,
  Part,
  modelAction,
  modelRef,
} from '@google-genkit/ai/model';
import { downloadRequestMedia } from '@google-genkit/ai/model/middleware';
import {
  GenerateContentCandidate as GeminiCandidate,
  InputContent as GeminiMessage,
  Part as GeminiPart,
  GoogleGenerativeAI,
} from '@google/generative-ai';
import process from 'process';
import z from 'zod';

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

const GeminiConfigSchema = z.object({
  safetySettings: z.array(SafetySettingsSchema).optional(),
});

export const geminiPro = modelRef({
  name: 'google-ai/gemini-pro',
  info: {
    label: 'Google AI - Gemini Pro',
    names: ['gemini-pro'],
    supports: {
      multiturn: true,
      media: false,
      tools: true,
    },
  },
  configSchema: GeminiConfigSchema,
});

export const geminiProVision = modelRef({
  name: 'google-ai/gemini-pro-vision',
  info: {
    label: 'Google AI - Gemini Pro Vision',
    names: ['gemini-pro-vision'],
    supports: {
      multiturn: true,
      media: true,
      tools: true,
    },
  },
  configSchema: GeminiConfigSchema,
});

export const geminiUltra = modelRef({
  name: 'google-ai/gemini-ultra',
  info: {
    label: 'Google AI - Gemini Ultra',
    names: ['gemini-ultra'],
    supports: {
      multiturn: true,
      media: false,
      tools: true,
    },
  },
  configSchema: GeminiConfigSchema,
});

export const SUPPORTED_MODELS = {
  'gemini-pro': geminiPro,
  'gemini-pro-vision': geminiProVision,
  'gemini-ultra': geminiUltra,
};

function toGeminiRole(role: MessageData['role']): string {
  switch (role) {
    case 'user':
      return 'user';
    case 'model':
      return 'model';
    case 'system':
      throw new Error('system role is not supported');
    case 'tool':
      return 'function';
    default:
      return 'user';
  }
}

function toInlineData(part: MediaPart): GeminiPart {
  const dataUrl = part.media.url;
  const b64Data = dataUrl.substring(dataUrl.indexOf(',')! + 1);
  const contentType =
    part.media.contentType ||
    dataUrl.substring(dataUrl.indexOf(':')! + 1, dataUrl.indexOf(';'));
  return { inlineData: { mimeType: contentType, data: b64Data } };
}

function toGeminiPart(part: Part): GeminiPart {
  if (part.text) return { text: part.text };
  if (part.media) return toInlineData(part);
  throw new Error('Only text and media parts are supported currently.');
}

function fromGeminiPart(part: GeminiPart): Part {
  if (part.text) return { text: part.text };
  throw new Error('Only support text for the moment.');
}

function toGeminiMessage(message: MessageData): GeminiMessage {
  return {
    role: toGeminiRole(message.role),
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
    case 'SAFETY':
      return 'blocked';
    case 'RECITATION':
      return 'other';
    default:
      return 'unknown';
  }
}

function fromGeminiCandidate(candidate: GeminiCandidate): CandidateData {
  return {
    index: candidate.index,
    message: {
      role: 'model',
      content: candidate.content.parts.map(fromGeminiPart),
    },
    finishReason: fromGeminiFinishReason(candidate.finishReason),
    finishMessage: candidate.finishMessage,
    custom: {
      safetyRatings: candidate.safetyRatings,
      citationMetadata: candidate.citationMetadata,
    },
  };
}

/**
 *
 */
export function googleAIModel(name: string, apiKey?: string): ModelAction {
  const modelName = `google-ai/${name}`;
  if (!apiKey)
    apiKey = process.env.GOOGLE_GENAI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!apiKey)
    throw new Error(
      'please pass in the API key or set the GOOGLE_GENAI_API_KEY or GOOGLE_API_KEY environment variable'
    );
  const client = new GoogleGenerativeAI(apiKey).getGenerativeModel({
    model: name,
  });
  if (!SUPPORTED_MODELS[name]) throw new Error(`Unsupported model: ${name}`);
  return modelAction(
    {
      name: modelName,
      ...SUPPORTED_MODELS[name].info,
      // since gemini api doesn't support downloading media from http(s)
      use: [downloadRequestMedia({ maxBytes: 1024 * 1024 * 10 })],
    },
    async (request) => {
      const messages = request.messages.map(toGeminiMessage);
      if (messages.length === 0) throw new Error('No messages provided.');
      const result = await client
        .startChat({
          history: messages.slice(0, messages.length - 1),
          generationConfig: {
            candidateCount: request.candidates,
            temperature: request.config?.temperature,
            maxOutputTokens: request.config?.maxOutputTokens,
            topK: request.config?.topK,
            topP: request.config?.topP,
            stopSequences: request.config?.stopSequences,
          },
          safetySettings: request.config?.custom?.safetySettings,
        })
        .sendMessage(messages[messages.length - 1].parts);

      if (!result.response.candidates?.length)
        throw new Error('No valid candidates returned.');
      return {
        candidates: result.response.candidates?.map(fromGeminiCandidate) || [],
        custom: result.response,
      };
    }
  );
}
