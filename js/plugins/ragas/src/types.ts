import * as z from 'zod';

export const RagasDataPointSchema = z.object({
  input: z.string(),
  output: z.string().optional(),
  context: z.array(z.string()).optional(),
});
export type RagasDataPoint = z.infer<RagasDataPointZodType>;

export type RagasDataPointZodType = typeof RagasDataPointSchema;

export enum RagasMetric {
  FAITHFULNESS = 'FAITHFULNESS',
  CONTEXT_PRECISION = 'CONTEXT_PRECISION',
  ANSWER_RELEVANCY = 'ANSWER_RELEVANCY',
}
