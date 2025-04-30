/**
 * Copyright 2025 Google LLC
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

import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';

import { FunctionDeclaration, Schema, Type } from './types';

/**
 * A placeholder name for the zod schema when converting to JSON schema. The
 * name is not important and will not be used by users.
 */
const PLACEHOLDER_ZOD_SCHEMA_NAME = 'placeholderZodSchemaName';

/**
 * Represents the possible JSON schema types.
 */
export type JSONSchemaType =
  | 'string'
  | 'number'
  | 'integer'
  | 'object'
  | 'array'
  | 'boolean'
  | 'null';

/**
 * A subset of JSON Schema according to 2020-12 JSON Schema draft.
 *
 * Represents a subset of a JSON Schema object that can be used by Gemini API.
 * The difference between this interface and the Schema interface is that this
 * interface is compatible with OpenAPI 3.1 schema objects while the
 * types.Schema interface @see {@link Schema} is used to make API call to
 * Gemini API.
 */
export interface JSONSchema {
  /**
   * Validation succeeds if the type of the instance matches the type
   * represented by the given type, or matches at least one of the given types
   * in the array.
   */
  type?: JSONSchemaType | JSONSchemaType[];

  /**
   * Defines semantic information about a string instance (e.g., "date-time",
   * "email").
   */
  format?: string;

  /**
   * A preferably short description about the purpose of the instance
   * described by the schema. This is not supported for Gemini API.
   */
  title?: string;

  /**
   * An explanation about the purpose of the instance described by the
   * schema.
   */
  description?: string;

  /**
   * This keyword can be used to supply a default JSON value associated
   * with a particular schema. The value should be valid according to the
   * schema.
   */
  default?: unknown;

  /**
   * Used for arrays. This keyword is used to define the schema of the elements
   * in the array.
   */
  items?: JSONSchema;

  /**
   * Key word for arrays. Specify the minimum number of elements in the array.
   */
  minItems?: string;

  /**
   * Key word for arrays. Specify the maximum number of elements in the array.e
   */
  maxItems?: string;

  /**
   * Used for specify the possible values for an enum.
   */
  enum?: unknown[];

  /**
   * Used for objects. This keyword is used to define the schema of the
   * properties in the object.
   */
  properties?: Record<string, JSONSchema>;

  /**
   * Used for objects. This keyword is used to specify the properties of the
   * object that are required to be present in the instance.
   */
  required?: string[];

  /**
   * The key word for objects. Specify the minimum number of properties in the
   * object.
   */
  minProperties?: string;

  /**
   * The key word for objects. Specify the maximum number of properties in the
   * object.
   */
  maxProperties?: string;

  /**
   * Used for numbers. Specify the minimum value for a number.
   */
  minimum?: number;

  /**
   * Used for numbers. specify the maximum value for a number.
   */
  maximum?: number;

  /**
   * Used for strings. The keyword to specify the minimum length of the
   * string.
   */
  minLength?: string;

  /**
   * Used for strings. The keyword to specify the maximum length of the
   * string.
   */
  maxLength?: string;

  /**
   * Used for strings. Key word to specify a regular
   * expression (ECMA-262) matches the instance successfully.
   */
  pattern?: string;

  /**
   * Used for Union types and Intersection types. This keyword is used to define
   * the schema of the possible values.
   */
  anyOf?: JSONSchema[];
}

const jsonSchemaTypeValidator = z.enum([
  'string',
  'number',
  'integer',
  'object',
  'array',
  'boolean',
  'null',
]);

// Handles all types and arrays of all types.
const schemaTypeUnion = z.union([
  jsonSchemaTypeValidator,
  z.array(jsonSchemaTypeValidator),
]);

// Declare the type for the schema variable.
type jsonSchemaValidatorType = z.ZodType<JSONSchema>;

const jsonSchemaValidator: jsonSchemaValidatorType = z.lazy(() => {
  return z
    .object({
      // --- Type ---
      type: schemaTypeUnion.optional(),

      // --- Annotations ---
      format: z.string().optional(),
      title: z.string().optional(),
      description: z.string().optional(),
      default: z.unknown().optional(),

      // --- Array Validations ---
      items: jsonSchemaValidator.optional(),
      minItems: z.coerce.string().optional(),
      maxItems: z.coerce.string().optional(),
      // --- Generic Validations ---
      enum: z.array(z.unknown()).optional(),

      // --- Object Validations ---
      properties: z.record(z.string(), jsonSchemaValidator).optional(),
      required: z.array(z.string()).optional(),
      minProperties: z.coerce.string().optional(),
      maxProperties: z.coerce.string().optional(),

      // --- Numeric Validations ---
      minimum: z.number().optional(),
      maximum: z.number().optional(),

      // --- String Validations ---
      minLength: z.coerce.string().optional(),
      maxLength: z.coerce.string().optional(),
      pattern: z.string().optional(),

      // --- Schema Composition ---
      anyOf: z.array(jsonSchemaValidator).optional(),

      // --- Additional Properties --- This field is not included in the
      // JSONSchema, will not be communicated to the model, it is here purely
      // for enabling the zod validation strict mode.
      additionalProperties: z.boolean().optional(),
    })
    .strict();
});

/**
 * Converts a Zod object into the Gemini schema format.
 *
 * [Experimental] This function first validates the structure of the input
 * `zodSchema` object against an internal representation of JSON Schema (see
 * {@link JSONSchema}).
 * Any mismatch in data types and inrecongnized properties will cause an error.
 *
 * @param zodSchema The Zod schema object to convert. Its structure is validated
 * against the {@link JSONSchema} interface before conversion to JSONSchema
 * schema.
 * @return The resulting Schema object. @see {@link Schema}
 * @throws {ZodError} If the input `zodSchema` does not conform to the expected
 * JSONSchema structure during the initial validation step.
 * @see {@link JSONSchema} The interface used to validate the input `zodSchema`.
 */
export function schemaFromZodType(zodSchema: z.ZodType): Schema {
  return processZodSchema(zodSchema);
}

function processZodSchema(zodSchema: z.ZodType): Schema {
  const jsonSchema = zodToJsonSchema(zodSchema, PLACEHOLDER_ZOD_SCHEMA_NAME)
    .definitions![PLACEHOLDER_ZOD_SCHEMA_NAME] as Record<string, unknown>;
  const validatedJsonSchema = jsonSchemaValidator.parse(jsonSchema);
  return processJsonSchema(validatedJsonSchema);
}

/*
Handle type field:
The resulted type field in JSONSchema form zod_to_json_schema can be either
an array consist of primitive types or a single primitive type.
This is due to the optimization of zod_to_json_schema, when the types in the
union are primitive types without any additional specifications,
zod_to_json_schema will squash the types into an array instead of put them
in anyOf fields. Otherwise, it will put the types in anyOf fields.
See the following link for more details:
https://github.com/zodjs/zod-to-json-schema/blob/main/src/index.ts#L101
The logic here is trying to undo that optimization, flattening the array of
types to anyOf fields.
                                 type field
                                      |
                            ___________________________
                           /                           \
                          /                              \
                         /                                \
                       Array                              Type.*
                /                  \                       |
      Include null.              Not included null     type = Type.*.
      [null, Type.*, Type.*]     multiple types.
      [null, Type.*]             [Type.*, Type.*]
            /                                \
      remove null                             \
      add nullable = true                      \
       /                    \                   \
    [Type.*]           [Type.*, Type.*]          \
 only one type left     multiple types left       \
 add type = Type.*.           \                  /
                               \                /
                         not populate the type field in final result
                           and make the types into anyOf fields
                          anyOf:[{type: 'Type.*'}, {type: 'Type.*'}];
*/
function flattenTypeArrayToAnyOf(typeList: string[], resultingSchema: Schema) {
  if (typeList.includes('null')) {
    resultingSchema['nullable'] = true;
  }
  const listWithoutNull = typeList.filter((type) => type !== 'null');

  if (listWithoutNull.length === 1) {
    resultingSchema['type'] = Object.keys(Type).includes(
      listWithoutNull[0].toUpperCase()
    )
      ? Type[listWithoutNull[0].toUpperCase() as keyof typeof Type]
      : Type.TYPE_UNSPECIFIED;
  } else {
    resultingSchema['anyOf'] = [];
    for (const i of listWithoutNull) {
      resultingSchema['anyOf'].push({
        type: Object.keys(Type).includes(i.toUpperCase())
          ? Type[i.toUpperCase() as keyof typeof Type]
          : Type.TYPE_UNSPECIFIED,
      });
    }
  }
}

function processJsonSchema(_jsonSchema: JSONSchema): Schema {
  const genAISchema: Schema = {};
  const schemaFieldNames = ['items'];
  const listSchemaFieldNames = ['anyOf'];
  const dictSchemaFieldNames = ['properties'];

  if (_jsonSchema['type'] && _jsonSchema['anyOf']) {
    throw new Error('type and anyOf cannot be both populated.');
  }

  /*
  This is to handle the nullable array or object. The _jsonSchema will
  be in the format of {anyOf: [{type: 'null'}, {type: 'object'}]}. The
  logic is to check if anyOf has 2 elements and one of the element is null,
  if so, the anyOf field is unnecessary, so we need to get rid of the anyOf
  field and make the schema nullable. Then use the other element as the new
  _jsonSchema for processing. This is becuase the backend doesn't have a null
  type.
  This has to be checked before we process any other fields.
  For example:
    const objectNullable = z.object({
      nullableArray: z.array(z.string()).nullable(),
    });
  Will have the raw _jsonSchema as:
  {
    type: 'OBJECT',
    properties: {
        nullableArray: {
           anyOf: [
              {type: 'null'},
              {
                type: 'array',
                items: {type: 'string'},
              },
            ],
        }
    },
    required: [ 'nullableArray' ],
  }
  Will result in following schema compitable with Gemini API:
    {
      type: 'OBJECT',
      properties: {
         nullableArray: {
            nullable: true,
            type: 'ARRAY',
            items: {type: 'string'},
         }
      },
      required: [ 'nullableArray' ],
    }
  */
  const incomingAnyOf = _jsonSchema['anyOf'] as JSONSchema[];
  if (incomingAnyOf != null && incomingAnyOf.length == 2) {
    if (incomingAnyOf[0]!['type'] === 'null') {
      genAISchema['nullable'] = true;
      _jsonSchema = incomingAnyOf![1];
    } else if (incomingAnyOf[1]!['type'] === 'null') {
      genAISchema['nullable'] = true;
      _jsonSchema = incomingAnyOf![0];
    }
  }

  if (_jsonSchema['type'] instanceof Array) {
    flattenTypeArrayToAnyOf(_jsonSchema['type'], genAISchema);
  }

  for (const [fieldName, fieldValue] of Object.entries(_jsonSchema)) {
    // Skip if the fieldvalue is undefined or null.
    if (fieldValue == null) {
      continue;
    }

    if (fieldName == 'type') {
      if (fieldValue === 'null') {
        throw new Error(
          'type: null can not be the only possible type for the field.'
        );
      }
      if (fieldValue instanceof Array) {
        // we have already handled the type field with array of types in the
        // beginning of this function.
        continue;
      }
      genAISchema['type'] = Object.keys(Type).includes(fieldValue.toUpperCase())
        ? fieldValue.toUpperCase()
        : Type.TYPE_UNSPECIFIED;
    } else if (schemaFieldNames.includes(fieldName)) {
      (genAISchema as Record<string, unknown>)[fieldName] = processJsonSchema(
        fieldValue
      ) as Record<string, unknown>;
    } else if (listSchemaFieldNames.includes(fieldName)) {
      const listSchemaFieldValue: Array<Schema> = [];
      for (const item of fieldValue) {
        if (item['type'] == 'null') {
          genAISchema['nullable'] = true;
          continue;
        }
        listSchemaFieldValue.push(
          processJsonSchema(item as JSONSchema) as Schema
        );
      }
      (genAISchema as Record<string, unknown>)[fieldName] =
        listSchemaFieldValue;
    } else if (dictSchemaFieldNames.includes(fieldName)) {
      const dictSchemaFieldValue: Record<string, Schema> = {};
      for (const [key, value] of Object.entries(
        fieldValue as Record<string, unknown>
      )) {
        dictSchemaFieldValue[key] = processJsonSchema(
          value as JSONSchema
        ) as Schema;
      }
      (genAISchema as Record<string, unknown>)[fieldName] =
        dictSchemaFieldValue;
    } else {
      if (fieldName === 'enum') {
        genAISchema['format'] = 'enum';
      }
      // additionalProperties is not included in JSONSchema, skipping it.
      if (fieldName === 'additionalProperties') {
        continue;
      }
      (genAISchema as Record<string, unknown>)[fieldName] = fieldValue;
    }
  }
  return genAISchema;
}

/**
 * Object for passing the details of the zod function schema.
 * This is to set up the named parameters for the functionDeclarationFromZod
 * function.
 */
export interface ZodFunction {
  // The name of the function.
  name: string;
  // The zod function schema. This any here is to support the zod function with no arguments.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  zodFunctionSchema: z.ZodFunction<z.ZodTuple<any, z.ZodTypeAny>, z.ZodTypeAny>;
}

/**
 * Converts a Zod function schema definition into a FunctionDeclaration object.
 *
 * [Experimental] This function help to convert the zod function to the function
 * declaration format. Currently, the function only support the function with
 * one parameter value, the parameter can be object or void.
 *
 * @param zodFunction The zodFunction object for passing the name and zod
 *     function
 * schema. see {@link ZodFunction} for more details.
 * @return The resulting FunctionDeclaration object. @see {@link FunctionDeclaration}
 * @throws {ZodError} If the input `zodFunction` contains paramters that can not
 * be converteed to Schema object @see {@link Schema}
 * @throws {Error} If the input `zodFunction` contains more than one parameter
 * or the parameter is not object.
 */
export function functionDeclarationFromZodFunction(
  zodFunction: ZodFunction
): FunctionDeclaration {
  const functionDeclaration: FunctionDeclaration = {};

  // Process the name of the function.
  functionDeclaration.name = zodFunction.name;
  // Process the description of the function.
  functionDeclaration.description =
    zodFunction.zodFunctionSchema._def.description;
  // Process the return value of the function.
  const zodFunctionReturn = zodFunction.zodFunctionSchema._def.returns;
  if (!(zodFunctionReturn._def.typeName === 'ZodVoid')) {
    functionDeclaration.response = processZodSchema(zodFunctionReturn);
  }
  // Process the parameters of the function.
  const functionParams = zodFunction.zodFunctionSchema._def.args._def
    .items as z.ZodTypeAny[];
  if (functionParams.length > 1) {
    throw new Error(
      'Multiple positional parameters are not supported at the moment. Function parameters must be defined using a single object with named properties.'
    );
  }
  if (functionParams.length === 1) {
    const param = functionParams[0];
    if (param._def.typeName === 'ZodObject') {
      functionDeclaration.parameters = processZodSchema(functionParams[0]);
    } else {
      if (param._def.typeName === 'ZodOptional') {
        throw new Error(
          'Supllying only optional parameter is not supported at the moment. You can make all the fields inside the parameter object as optional.'
        );
      }
      if (!(param._def.typeName === 'ZodVoid')) {
        throw new Error(
          'Function parameter is not object and not void, please check the parameter type. Please wrap the parameter in an object with named properties.'
        );
      }
    }
  }

  return functionDeclaration;
}
