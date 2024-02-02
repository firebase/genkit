import {
  GoogleGenerativeAI,
  InputContent as GeminiMessage,
  Part as GeminiPart,
  GenerateContentCandidate as GeminiCandidate,
} from '@google/generative-ai';
import process from 'process';
import {
  ModelAction,
  Part,
  MessageData,
  CandidateData,
} from '@google-genkit/ai/model';
import { modelAction } from '@google-genkit/ai/model';

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

function toGeminiPart(part: Part): GeminiPart {
  if (part.text) return { text: part.text };
  throw new Error('Only support text for the moment.');
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

export function googleAIModel(name: string, apiKey?: string): ModelAction {
  if (!apiKey) apiKey = process.env.GOOGLE_API_KEY;
  if (!apiKey)
    throw new Error(
      'please pass in the API key or set GOOGLE_API_KEY environment variable'
    );
  const client = new GoogleGenerativeAI(apiKey).getGenerativeModel({
    model: name,
  });
  return modelAction({ name: `google-ai/${name}` }, async (request) => {
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
      })
      .sendMessage(messages[messages.length - 1].parts);

    if (!result.response.candidates?.length)
      throw new Error('No valid candidates returned.');
    return {
      candidates: result.response.candidates?.map(fromGeminiCandidate) || [],
      custom: result.response,
    };
  });
}
