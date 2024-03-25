import { z } from 'zod';

export const ScoreSchema = z.object({
  score: z.number().optional(),
  // TODO: use StatusSchema
  error: z.string().optional(),
  details: z
    .object({
      reasoning: z.string().optional(),
    })
    .passthrough()
    .optional(),
});

export const EvaluatorResponseSchema = z.array(
  z.object({
    sampleIndex: z.number(),
    testCaseId: z.string().optional(),
    evaluation: ScoreSchema,
  })
);

export type EvaluatorResponse = z.infer<typeof EvaluatorResponseSchema>;
