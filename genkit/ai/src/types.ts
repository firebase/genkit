import { z } from 'zod';
import { Action } from '@google-genkit/common';
import { zodToJsonSchema } from 'zod-to-json-schema';

export const ModelIdSchema = z.object({
  modelProvider: z.string().readonly(),
  modelName: z.string().readonly(),
});

export type ModelId = z.infer<typeof ModelIdSchema>;

export const LlmStatsSchema = z.object({
  latencyMs: z.number().optional(),
  inputTokenCount: z.number().optional(),
  outputTokenCount: z.number().optional(),
});

export type LlmStats = z.infer<typeof LlmStatsSchema>;

export const ToolSchema = z.object({
  name: z.string(),
  description: z.string().optional(),
  schema: z.any(),
});

export type Tool = z.infer<typeof ToolSchema>;

export const ToolCallSchema = z.object({
  toolName: z.string(),
  arguments: z.any(),
});

export type ToolCall = z.infer<typeof ToolCallSchema>;

export const LlmResponseSchema = z.object({
  completion: z.string(),
  toolCalls: z.array(ToolCallSchema).optional(),
  stats: LlmStatsSchema,
});

export type LlmResponse = z.infer<typeof LlmResponseSchema>;

/**
 * Converts actions to tool definition sent to model inputs.
 */
export function toToolWireFormat(
  actions?: Action<any, any>[]
): z.infer<typeof ToolSchema>[] | undefined {
  if (!actions) return undefined;
  return actions.map((a) => {
    return {
      name: a.__action.name,
      description: a.__action.description,
      schema: {
        input: zodToJsonSchema(a.__action.inputSchema),
        output: zodToJsonSchema(a.__action.outputSchema),
      },
    };
  });
}

// Streaming callback function.
export type StreamingCallbackFn = (text: string) => void;

// Streaming
export interface StreamingCallback {
  onChunk: StreamingCallbackFn;
}

// Does it even make sense to have common options? since they are referenced differently in different LLMs.
export const CommonLlmOptions = z.object({
  temperature: z.number().optional(),
  topK: z.number().optional(),
  topP: z.number().optional(),
});
