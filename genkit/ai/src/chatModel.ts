import * as z from 'zod';
import {
  ToolSchema,
  toToolWireFormat,
  LlmResponse,
  LlmResponseSchema,
  StreamingCallback,
} from './types';
import { Action, action } from '@google-genkit/common';
import * as registry from '@google-genkit/common/registry';
import { setCustomMetadataAttribute } from '@google-genkit/common/tracing';

// Message roles
export enum Role {
  User = 'user',
  Model = 'model',
  System = 'system',
  Tool = 'tool',
}

const MessageSchema = z.object({
  role: z.nativeEnum(Role),
  message: z.string(),
  name: z.string().optional(),
  toolCallId: z.string().optional(),
});

export type Message = z.infer<typeof MessageSchema>;

export const ChatModelInput = z.object({
  messages: z.array(MessageSchema),
  tools: z.array(ToolSchema).optional(),
});

export type ChatModelFn<ChatModelOptions extends z.ZodType> = (
  input: z.infer<typeof ChatModelInput>,
  options?: z.infer<ChatModelOptions>,
  streamingCallback?: StreamingCallback
) => Promise<LlmResponse>;

export interface ChatModel<ModelOptions extends z.ZodType> {
  generateMessage: ChatModelFn<ModelOptions>;
  queryOptionsType: ModelOptions;
}

// Use this - rather than adding options to ChatModelInput (?)
function makeChatLlmInputType<ChatModelOptions extends z.ZodType>(
  customOptionsType: ChatModelOptions
) {
  return ChatModelInput.extend({
    options: customOptionsType.optional(),
  });
}

export type ChatLlmAction<
  I extends z.ZodType,
  O extends z.ZodType,
  CustomOptions extends z.ZodType
> = Action<I, O> & { __customOptionsType: CustomOptions };

function withMetadata<
  I extends z.ZodType,
  O extends z.ZodType,
  CustomOptions extends z.ZodType
>(
  model: Action<I, O>,
  customOptionsType: CustomOptions
): ChatLlmAction<I, O, CustomOptions> {
  const withMeta = model as ChatLlmAction<I, O, CustomOptions>;
  withMeta.__customOptionsType = customOptionsType;
  return withMeta;
}

/**
 * A veneer API for interacting with chat models.
 */
export async function generateMessage<
  I extends z.ZodType,
  O extends z.ZodType,
  CustomOptions extends z.ZodType
>(params: {
  model: ChatLlmAction<I, O, CustomOptions>;
  messages: Message[];
  streamingCallback?: StreamingCallback;
  tools?: Action<any, any>[];
  options?: z.infer<CustomOptions>;
}): Promise<LlmResponse> {
  return await params.model({
    messages: params.messages,
    options: params.options,
    tools: toToolWireFormat(params.tools),
  });
}

/**
 * Creates chat model for the provided {@link ChatModelFn} model implementation.
 */
export function chatModelFactory<ChatModelOptions extends z.ZodType>(
  provider: string,
  modelName: string,
  customOptionsType: ChatModelOptions,
  fn: ChatModelFn<ChatModelOptions>
) {
  const inputType = makeChatLlmInputType(customOptionsType);
  const model = action(
    {
      name: provider + '/' + modelName,
      input: inputType,
      output: LlmResponseSchema,
    },
    (i) => {
      setCustomMetadataAttribute('ai:type', 'generateMessage');

      return fn(
        {
          messages: i.messages,
          tools: i.tools,
        },
        i.options
      );
    }
  );
  registry.registerAction('chat-llm', `${provider}/${modelName}`, model);
  return withMetadata(model, customOptionsType);
}
