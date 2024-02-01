import * as z from 'zod';
import {
  ToolSchema,
  toToolWireFormat,
  LlmResponse,
  LlmResponseSchema,
  StreamingCallback,
  ModelId,
  StreamingCallbackFn,
} from './types';
import { Action, action } from '@google-genkit/common';
import * as registry from '@google-genkit/common/registry';
import {
  MultimodalPrompt,
  MultimodalPromptSchema,
  Prompt,
  PromptSchema,
  prompt,
} from './prompt';
import { setCustomMetadataAttribute } from '@google-genkit/common/tracing';
import { AsyncLocalStorage } from 'node:async_hooks';

const streamingAls = new AsyncLocalStorage<StreamingCallback>();

export const TextModelInput = z.object({
  prompt: PromptSchema.or(MultimodalPromptSchema),
  tools: z.array(ToolSchema).optional(),
});

function makeTextLlmInputType<TextModelOptions extends z.ZodType>(
  customOptionsType: TextModelOptions
) {
  return TextModelInput.extend({
    options: customOptionsType.optional(),
  });
}

function withMetadata<
  I extends z.ZodType,
  O extends z.ZodType,
  CustomOptions extends z.ZodType
>(
  model: Action<I, O>,
  customOptionsType: CustomOptions
): TextLlmAction<I, O, CustomOptions> {
  const withMeta = model as TextLlmAction<I, O, CustomOptions>;
  withMeta.__customOptionsType = customOptionsType;
  return withMeta;
}

/**
 * Creates text model actopm for the provided {@link TextModelFn} model implementation.
 */
export function textModelFactory<TextModelOptions extends z.ZodType>(
  provider: string,
  modelName: string,
  customOptionsType: TextModelOptions,
  fn: TextModelFn<TextModelOptions>
) {
  const inputType = makeTextLlmInputType(customOptionsType);
  const model = action(
    {
      name: provider + '/' + modelName,
      input: inputType,
      output: LlmResponseSchema,
    },
    (i) => {
      setCustomMetadataAttribute('ai:type', 'generateText');
      return fn(
        {
          prompt: i.prompt,
          tools: i.tools,
        },
        i.options,
        getStreamingCallback()
      );
    }
  );
  registry.registerAction('text-llm', `${provider}/${modelName}`, model);
  return withMetadata(model, customOptionsType);
}

export type TextModelFn<TextModelOptions extends z.ZodType> = (
  input: z.infer<typeof TextModelInput>,
  options?: z.infer<TextModelOptions>,
  streamingCallback?: StreamingCallback
) => Promise<LlmResponse>;

export type TextLlmAction<
  I extends z.ZodType,
  O extends z.ZodType,
  CustomOptions extends z.ZodType
> = Action<I, O> & { __customOptionsType: CustomOptions };

/**
 * A veneer for interacting with text models.
 */
export async function generateText<
  I extends z.ZodType,
  O extends z.ZodType,
  CustomOptions extends z.ZodType
>(params: {
  model?: TextLlmAction<I, O, CustomOptions>;
  prompt: string | Prompt | MultimodalPrompt;
  streamingCallback?: StreamingCallbackFn;
  tools?: Action<any, any>[];
  options?: z.infer<CustomOptions>;
}): Promise<LlmResponse> {
  const p =
    typeof params.prompt === 'string' ? prompt(params.prompt) : params.prompt;
  const model = resolveModel(params.model, p.metadata?.modelId);
  return await runWithStreamingCallback(
    params.streamingCallback,
    async () =>
      await model({
        prompt: p,
        options: params.options,
        tools: toToolWireFormat(params.tools),
      })
  );
}

function resolveModel<
  I extends z.ZodType,
  O extends z.ZodType,
  CustomOptions extends z.ZodType
>(model: TextLlmAction<I, O, CustomOptions> | undefined, modelId?: ModelId) {
  if (!model && modelId) {
    model = getTextModelFromRegistry(modelId);
    if (!model) {
      throw new Error(
        `No configured model found for provider ${modelId.modelProvider} and ` +
          `model name ${modelId.modelName}`
      );
    }
  }
  if (!model) {
    throw new Error(
      'Model information is missing. Either provide pass a model or a prompt with modelId.'
    );
  }
  return model;
}

function getTextModelFromRegistry(id: ModelId): TextLlmAction<any, any, any> {
  return registry.lookupAction(`/text-llm/${id.modelProvider}/${id.modelName}`);
}

/**
 * Executes provided functino with streaming callback in async local storage which can be retrieved
 * using {@link getStreamingCallback}.
 */
export function runWithStreamingCallback<O>(
  streamingCallbackFn: StreamingCallbackFn | undefined,
  fn: () => O
) {
  return streamingAls.run(
    streamingCallbackFn
      ? { onChunk: streamingCallbackFn }
      : { onChunk: () => null },
    fn
  );
}

/**
 * Retrieves the {@link StreamingCallback} previously set by {@link runWithStreamingCallback}
 */
export function getStreamingCallback(): StreamingCallback | undefined {
  return streamingAls.getStore();
}
