/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import Ajv, { ErrorObject } from 'ajv';
import { z } from 'zod';
import zodToJsonSchema, { JsonSchema7Type } from 'zod-to-json-schema';
import { GenkitError } from './error.js';
const ajv = new Ajv();

export { z }; // provide a consistent zod to use throughout genkit
export type JSONSchema = JsonSchema7Type;
const jsonSchemas = new WeakMap<z.ZodTypeAny, JSONSchema>();
const validators = new WeakMap<JSONSchema, ReturnType<typeof ajv.compile>>();

export interface ProvidedSchema {
  jsonSchema?: JSONSchema;
  schema?: z.ZodTypeAny;
}

export class ValidationError extends GenkitError {
  constructor({
    data,
    errors,
  }: {
    data: any;
    errors: ValidationErrorDetail[];
  }) {
    super({
      status: 'INVALID_ARGUMENT',
      message: `Schema validation failed. Parse Errors:\n\n${errors.map((e) => `- ${e.path}: ${e.message}`).join('\n')}\n\nProvided data:\n\n${JSON.stringify(data, null, 2)}`,
      detail: { errors },
    });
  }
}

/**
 * Convertes a Zod schema into a JSON schema, utilizing an in-memory cache for known objects.
 * @param options Provide a json schema and/or zod schema. JSON schema has priority.
 * @returns A JSON schema.
 */
export function toJsonSchema({
  jsonSchema,
  schema,
}: ProvidedSchema): JSONSchema {
  // if neither jsonSchema or schema is present, default to empty object representing 'any' in JSONSchema
  if (!jsonSchema && !schema) return {};
  if (jsonSchema) return jsonSchema;
  if (jsonSchemas.has(schema!)) return jsonSchemas.get(schema!)!;
  const outSchema = zodToJsonSchema(schema!);
  jsonSchemas.set(schema!, outSchema);
  return outSchema;
}

export interface ValidationErrorDetail {
  path: string;
  message: string;
}

function toErrorDetail(error: ErrorObject): ValidationErrorDetail {
  return {
    path: error.instancePath.substring(1).replace(/\//g, '.'),
    message: error.message!,
  };
}

export type ValidationResponse =
  | { valid: true; errors: never }
  | { valid: false; errors: ErrorObject[] };

export function validateSchema(
  data: unknown,
  options: ProvidedSchema
): { valid: boolean; errors?: any[] | null } {
  const toValidate = toJsonSchema(options);
  const validator = validators.get(toValidate) || ajv.compile(toValidate);
  const valid = validator(data) as boolean;
  const errors = validator.errors?.map((e) => e);
  return { valid, errors: errors?.map(toErrorDetail) };
}

export function parseSchema<T = unknown>(
  data: unknown,
  options: ProvidedSchema
): T {
  const { valid, errors } = validateSchema(data, options);
  if (!valid) throw new ValidationError({ data, errors: errors! });
  return data as T;
}
