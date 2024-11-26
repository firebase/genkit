import type { PromptMessage } from '@modelcontextprotocol/sdk/types.js' with { 'resolution-mode': 'import' };
import { MessageData, Part } from 'genkit';

const ROLE_MAP = {
  user: 'user',
  assistant: 'model',
} as const;

export function fromMcpPromptMessage(message: PromptMessage): MessageData {
  return {
    role: ROLE_MAP[message.role],
    content: [fromMcpPart(message.content)],
  };
}

export function fromMcpPart(part: PromptMessage['content']): Part {
  switch (part.type) {
    case 'text':
      return { text: part.text };
    case 'image':
      return {
        media: {
          contentType: part.mimeType,
          url: `data:${part.mimeType};base64,${part.data}`,
        },
      };
    case 'resource':
      return {};
  }
}
