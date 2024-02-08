import * as z from 'zod';
import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import {
  extendZodWithOpenApi,
  OpenAPIRegistry,
  OpenApiGeneratorV3,
} from '@asteasolutions/zod-to-openapi';

// Note: This is an experimental way to generate the Reflection API OpenAPI spec.

extendZodWithOpenApi(z);

// `z.any()` generates `{ nullable: true }` with no type set which is not valid OpenAPI spec.
// There's no way around this without defining a custom type. `z.array()` needs an inner type which runs into the same issue.

const SingularAny = z
  .union([z.string(), z.number(), z.bigint(), z.boolean(), z.object({})])
  .openapi('SingularAny');

const CustomAny = z
  .union([SingularAny, z.array(SingularAny)])
  .openapi('CustomAny');

// TODO: Figure out a way to do z.custom<JSONSchema7>() and have it generate a nullable object correctly.
const JSONSchema7 = z
  .object({})
  .describe(
    'A valid JSON Schema Draft 7 (http://json-schema.org/draft-07/schema) object.'
  )
  .nullish()
  .openapi('JSONSchema7');

const Action = z
  .object({
    key: z.string().describe('Action key consisting of action type and ID.'),
    name: z.string().describe('Action name.'),
    description: z
      .string()
      .describe('A description of what the action does.')
      .nullish(),
    inputSchema: JSONSchema7,
    outputSchema: JSONSchema7,
    metadata: z
      .record(z.string(), CustomAny)
      .describe('Metadata about the action (e.g. supported model features).')
      .nullish(),
  })
  .openapi('Action');

const registry = new OpenAPIRegistry();
registry.register('SingularAny', SingularAny);
registry.register('CustomAny', CustomAny);
registry.register('JSONSchema7', JSONSchema7);
registry.register('Action', Action);
registry.registerPath({
  method: 'get',
  path: '/api/actions',
  summary: 'Retrieves all runnable actions.',
  responses: {
    '200': {
      description: 'Success',
      content: {
        'application/json': {
          schema: z.record(z.string(), Action),
        },
      },
    },
  },
});
registry.registerPath({
  method: 'post',
  path: '/api/runAction',
  summary: 'Runs an action and returns the result.',
  request: {
    body: {
      content: {
        'application/json': {
          schema: z.object({
            key: z.string().describe('Action key.'),
            input: CustomAny.describe(
              'An input with the type that this action expects.'
            ),
          }),
        },
      },
    },
  },
  responses: {
    '200': {
      description: 'Success',
      content: {
        'application/json': {
          schema: CustomAny.describe(
            'An output with the type that this action returns.'
          ),
        },
      },
    },
  },
});

const generator = new OpenApiGeneratorV3(registry.definitions);
export const document = generator.generateDocument({
  openapi: '3.0.0',
  info: {
    version: '0.0.1',
    title: 'Genkit Reflection API',
    description:
      'A control API that allows clients to inspect app code to view actions, run them, and view the results.',
  },
});

if (!process.argv[2]) {
  throw Error(
    'Please provide an absolute path to output the generated API spec.'
  );
}

fs.writeFileSync(
  path.join(process.argv[2], 'reflectionApi.yaml'),
  yaml.dump(document),
  {
    encoding: 'utf-8',
  }
);