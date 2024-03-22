import { z } from 'zod';
import { EvalRunKeySchema } from '../eval/types';
import { EnvTypesSchema } from './apis';

export const ListEvalKeysRequestSchema = z.object({
  env: EnvTypesSchema.optional(),
  filter: z
    .object({
      actionId: z.string().optional(),
    })
    .optional(),
  // TODO: Add support for limit and continuation token
});

export type ListEvalKeysRequest = z.infer<typeof ListEvalKeysRequestSchema>;

export const ListEvalKeysResponseSchema = z.object({
  evalRunKeys: z.array(EvalRunKeySchema),
  // TODO: Add support continuation token
});

export type ListEvalKeysResponse = z.infer<typeof ListEvalKeysResponseSchema>;

export const GetEvalRunRequestSchema = z.object({
  env: EnvTypesSchema.optional(),
  // Eval run name in the form actions/{action}/evalRun/{evalRun}
  // where `action` can be blank e.g. actions/-/evalRun/{evalRun}
  name: z.string(),
});

export type GetEvalRunRequest = z.infer<typeof GetEvalRunRequestSchema>;
