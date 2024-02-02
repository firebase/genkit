import { Action, action } from '@google-genkit/common';
import { registerAction } from '@google-genkit/common/registry';
import { z } from 'zod';

export const PartSchema = z.object({
  text: z.string().optional(),
  media: z
    .object({
      contentType: z.string().optional(),
      uri: z
        .string()
        .describe('data: or https: uri containing the media content'),
    })
    .optional(),
  tool: z
    .object({
      ref: z
        .string()
        .describe('reference or id for distinguishing multiple tool calls'),
      name: z.string(),
      input: z.record(z.unknown()).optional(),
      output: z.record(z.unknown()).optional(),
    })
    .optional(),
});
export type Part = z.infer<typeof PartSchema>;

export const RoleSchema = z.enum(['system', 'user', 'model', 'tool']);
export type Role = z.infer<typeof RoleSchema>;

export const MessageSchema = z.object({
  role: RoleSchema,
  content: z.array(PartSchema),
});
export type MessageData = z.infer<typeof MessageSchema>;

export const ModelInfoSchema = z.object({
  names: z.array(z.string()),
  label: z.string().optional(),
  match: z.function(z.tuple([z.string()]), z.boolean()).optional(),
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
> & {
  custom?: CustomOptions;
};

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
> = Action<typeof GenerationRequestSchema, typeof GenerationResponseSchema> & {
  __customOptionsType: CustomOptionsSchema;
};

export function modelAction<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny
>(
  options: {
    name: string;
    customOptionsType?: CustomOptionsSchema;
  },
  runner: (request: GenerationRequest) => Promise<GenerationResponseData>
): ModelAction<CustomOptionsSchema> {
  const act = action(
    {
      name: options.name,
      description: `${options.name} GenAI model`,
      input: GenerationRequestSchema,
      output: GenerationResponseSchema,
    },
    runner
  );
  (act as any).__customOptionsType = options.customOptionsType || z.any();
  registerAction('model', options.name, act);
  return act as ModelAction<CustomOptionsSchema>;
}
