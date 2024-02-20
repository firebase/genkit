import { Action, action } from '@google-genkit/common';
import { z } from 'zod';

export const TextPartSchema = z.object({
  /** The text of the message. */
  text: z.string(),
  media: z.never().optional(),
  toolRequest: z.never().optional(),
  toolResponse: z.never().optional(),
});
export type TextPart = z.infer<typeof TextPartSchema>;

export const MediaPartSchema = z.object({
  text: z.never().optional(),
  media: z.object({
    /** The media content type. Inferred from data uri if not provided. */
    contentType: z.string().optional(),
    /** A `data:` or `https:` uri containing the media content.  */
    url: z.string(),
  }),
  toolRequest: z.never().optional(),
  toolResponse: z.never().optional(),
});
export type MediaPart = z.infer<typeof MediaPartSchema>;

export const ToolRequestPartSchema = z.object({
  text: z.never().optional(),
  media: z.never().optional(),
  /** A request for a tool to be executed, usually provided by a model. */
  toolRequest: z.object({
    /** The call id or reference for a specific request. */
    ref: z.string().optional(),
    /** The name of the tool to call. */
    name: z.string(),
    /** The input parameters for the tool, usually a JSON object. */
    input: z.unknown().optional(),
  }),
  toolResponse: z.never().optional(),
});
export type ToolRequestPart = z.infer<typeof ToolRequestPartSchema>;

export const ToolResponsePartSchema = z.object({
  text: z.never().optional(),
  media: z.never().optional(),
  toolRequest: z.never().optional(),
  /** A provided response to a tool call. */
  toolResponse: z.object({
    /** The call id or reference for a specific request. */
    ref: z.string().optional(),
    /** The name of the tool. */
    name: z.string(),
    /** The output data returned from the tool, usually a JSON object. */
    output: z.unknown().optional(),
  }),
});
export type ToolResponsePart = z.infer<typeof ToolResponsePartSchema>;

export const PartSchema = z.union([
  TextPartSchema,
  MediaPartSchema,
  ToolRequestPartSchema,
  ToolResponsePartSchema,
]);
export type Part = z.infer<typeof PartSchema>;

export const RoleSchema = z.enum(['system', 'user', 'model', 'tool']);
export type Role = z.infer<typeof RoleSchema>;

export const MessageSchema = z.object({
  role: RoleSchema,
  content: z.array(PartSchema),
});
export type MessageData = z.infer<typeof MessageSchema>;

export const ModelInfoSchema = z.object({
  /** Acceptable names for this model (e.g. different versions). */
  names: z.array(z.string()).optional(),
  /** Friendly label for this model (e.g. "Google AI - Gemini Pro") */
  label: z.string().optional(),
  /** Supported model capabilities. */
  supports: z
    .object({
      /** Model can process historical messages passed with a prompt. */
      multiturn: z.boolean().optional(),
      /** Model can process media as part of the prompt (multimodal input). */
      media: z.boolean().optional(),
      /** Model can perform tool calls. */
      tools: z.boolean().optional(),
    })
    .optional(),
});
export type ModelInfo = z.infer<typeof ModelInfoSchema>;

export const ToolDefinitionSchema = z.object({
  name: z.string(),
  inputSchema: z
    .record(z.any())
    .describe('Valid JSON Schema representing the input of the tool.'),
  outputSchema: z
    .record(z.any())
    .describe('Valid JSON Schema describing the output of the tool.')
    .optional(),
});
export type ToolDefinition = z.infer<typeof ToolDefinitionSchema>;

export const GenerationConfig = z.object({
  temperature: z.number().optional(),
  maxOutputTokens: z.number().optional(),
  topK: z.number().optional(),
  topP: z.number().optional(),
  custom: z.record(z.any()).optional(),
  stopSequences: z.array(z.string()).optional(),
});
export type GenerationConfig<CustomOptions = any> = z.infer<
  typeof GenerationConfig
> &
  CustomOptions;

const OutputConfigSchema = z.object({
  format: z.enum(['json', 'text']).optional(),
  schema: z.record(z.any()).optional(),
});
export type OutputConfig = z.infer<typeof OutputConfigSchema>;

export const GenerationRequestSchema = z.object({
  messages: z.array(MessageSchema),
  config: GenerationConfig.optional(),
  tools: z.array(ToolDefinitionSchema).optional(),
  output: OutputConfigSchema.optional(),
  candidates: z.number().optional(),
});
export type GenerationRequest = z.infer<typeof GenerationRequestSchema>;

export const GenerationUsageSchema = z.object({
  inputTokens: z.number().optional(),
  outputTokens: z.number().optional(),
  totalTokens: z.number().optional(),
  custom: z.record(z.number()).optional(),
});
export type GenerationUsage = z.infer<typeof GenerationUsageSchema>;

export const CandidateSchema = z.object({
  index: z.number(),
  message: MessageSchema,
  usage: GenerationUsageSchema.optional(),
  finishReason: z.enum(['stop', 'length', 'blocked', 'other', 'unknown']),
  finishMessage: z.string().optional(),
  custom: z.unknown(),
});
export type CandidateData = z.infer<typeof CandidateSchema>;

export const CandidateErrorSchema = z.object({
  index: z.number(),
  code: z.enum(['blocked', 'other', 'unknown']),
  message: z.string().optional(),
});
export type CandidateError = z.infer<typeof CandidateErrorSchema>;

export const GenerationResponseSchema = z.object({
  candidates: z.array(CandidateSchema),
  usage: GenerationUsageSchema.optional(),
  custom: z.unknown(),
});
export type GenerationResponseData = z.infer<typeof GenerationResponseSchema>;

export type ModelAction<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny
> = Action<
  typeof GenerationRequestSchema,
  typeof GenerationResponseSchema,
  { model: ModelInfo }
> & {
  __customOptionsType: CustomOptionsSchema;
};

export interface ModelMiddleware {
  (
    req: GenerationRequest,
    next: (req?: GenerationRequest) => Promise<GenerationResponseData>
  ): Promise<GenerationResponseData>;
}

/**
 *
 */
export function modelWithMiddleware(
  model: ModelAction,
  middleware: ModelMiddleware[]
): ModelAction {
  const wrapped = (async (req: GenerationRequest) => {
    const dispatch = async (index: number, req: GenerationRequest) => {
      if (index === middleware.length) {
        // end of the chain, call the original model action
        return await model(req);
      }

      const currentMiddleware = middleware[index];
      return currentMiddleware(req, async (modifiedReq) =>
        dispatch(index + 1, modifiedReq || req)
      );
    };

    return await dispatch(0, req);
  }) as ModelAction;
  wrapped.__action = model.__action;
  return wrapped;
}

/**
 *
 */
export function modelAction<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny
>(
  options: {
    name: string;
    /** Alternate acceptable names for this model (e.g. different versions). */
    names?: string[];
    /** Capabilities this model supports. */
    supports?: ModelInfo['supports'];
    /** Custom options schema for this model. */
    customOptionsType?: CustomOptionsSchema;
    /** Descriptive name for this model e.g. 'Google AI - Gemini Pro'. */
    label?: string;
    tools?: Action<any, any>[];
    use?: ModelMiddleware[];
  },
  runner: (request: GenerationRequest) => Promise<GenerationResponseData>
): ModelAction<CustomOptionsSchema> {
  const label = options.label || `${options.name} GenAI model`;
  const act = action(
    {
      name: options.name,
      description: label,
      input: GenerationRequestSchema,
      output: GenerationResponseSchema,
      metadata: {
        model: {
          label,
          names: options.names,
          supports: options.supports,
        },
      },
    },
    runner
  );
  Object.assign(act, {
    __customOptionsType: options.customOptionsType || z.unknown(),
  });
  if (options.use?.length) {
    return modelWithMiddleware(
      act as ModelAction,
      options.use
    ) as ModelAction<CustomOptionsSchema>;
  }
  return act as ModelAction<CustomOptionsSchema>;
}

export interface ModelReference<CustomOptions extends z.ZodTypeAny> {
  name: string;
  configSchema?: CustomOptions;
  info?: ModelInfo;
}

/**
 *
 */
export function modelRef<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny
>(
  options: ModelReference<CustomOptionsSchema>
): ModelReference<CustomOptionsSchema> {
  return { ...options };
}
