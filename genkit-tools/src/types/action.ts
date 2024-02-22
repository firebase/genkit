import { z } from 'zod';
import { extendZodWithOpenApi } from '@asteasolutions/zod-to-openapi';

extendZodWithOpenApi(z);

// `z.any()` generates `{ nullable: true }` with no type set which is not valid OpenAPI spec.
// There's no way around this without defining a custom type. `z.array()` needs an inner type which runs into the same issue.

export const SingularAnySchema = z
  .union([z.string(), z.number(), z.bigint(), z.boolean(), z.object({})])
  .openapi('SingularAny');

export const CustomAnySchema = z
  .union([SingularAnySchema, z.array(SingularAnySchema)])
  .openapi('CustomAny');

// TODO: Figure out a way to do z.custom<JSONSchema7>() and have it generate a nullable object correctly.
export const JSONSchema7Schema = z
  .object({})
  .describe(
    'A JSON Schema Draft 7 (http://json-schema.org/draft-07/schema) object.'
  )
  .nullish()
  .openapi('JSONSchema7');

export const ActionSchema = z
  .object({
    key: z.string().describe('Action key consisting of action type and ID.'),
    name: z.string().describe('Action name.'),
    description: z
      .string()
      .describe('A description of what the action does.')
      .nullish(),
    inputSchema: JSONSchema7Schema,
    outputSchema: JSONSchema7Schema,
    metadata: z
      .record(z.string(), CustomAnySchema)
      .describe('Metadata about the action (e.g. supported model features).')
      .nullish(),
  })
  .openapi('Action');

export type Action = z.infer<typeof ActionSchema>;
