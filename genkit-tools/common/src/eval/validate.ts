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

import Ajv, { ErrorObject, JSONSchemaType } from 'ajv';
import addFormats from 'ajv-formats';
import { getDatasetStore } from '.';
import { RuntimeManager } from '../manager';
import {
  Action,
  InferenceDatasetSchema,
  ValidateDataRequest,
  ValidateDataResponse,
} from '../types';

// Setup for AJV
type JSONSchema = JSONSchemaType<any> | any;
const ajv = new Ajv();
addFormats(ajv);

/**
 * Validate given data against a target action. Intended to be used via the
 * reflection API.
 */
export async function validateSchema(
  manager: RuntimeManager,
  request: ValidateDataRequest
): Promise<ValidateDataResponse> {
  const { dataSource, actionRef } = request;
  const { datasetId, data } = dataSource;
  if (!datasetId && !data) {
    throw new Error(`Either 'data' or 'datasetId' must be provided`);
  }
  const targetAction = await getAction(manager, actionRef);
  const targetSchema = targetAction?.inputSchema;
  if (!targetAction) {
    throw new Error(`Could not find matching action for ${actionRef}`);
  }
  if (!targetSchema) {
    return { valid: true };
  }

  const errorsMap: Record<string, any> = {};

  if (datasetId) {
    const datasetStore = await getDatasetStore();
    const dataset = await datasetStore.getDataset(datasetId);
    if (dataset.length === 0) {
      return { valid: true };
    }
    dataset.forEach((sample, index) => {
      const response = validate(targetSchema, sample.input);
      if (!response.valid) {
        errorsMap[sample.testCaseId] = response.errors;
      }
    });

    return Object.keys(errorsMap).length === 0
      ? { valid: true }
      : { valid: false, errors: errorsMap };
  } else {
    const dataset = InferenceDatasetSchema.parse(data);
    dataset.forEach((sample, index) => {
      const response = validate(targetSchema, sample.input);
      if (!response.valid) {
        errorsMap[index.toString()] = response.errors;
      }
    });
    return Object.keys(errorsMap).length === 0
      ? { valid: true }
      : { valid: false, errors: errorsMap };
  }
}

function validate(
  jsonSchema: JSONSchema,
  data: unknown
): { valid: boolean; errors?: Record<string, any> } {
  const validator = ajv.compile(jsonSchema);
  const valid = validator(data) as boolean;
  const errors = validator.errors?.map((e) => e);
  return { valid, errors: errors?.map(toErrorDetail) };
}

function toErrorDetail(error: ErrorObject) {
  return {
    path: error.instancePath.substring(1).replace(/\//g, '.') || '(root)',
    message: error.message!,
  };
}

async function getAction(
  manager: RuntimeManager,
  actionRef: string
): Promise<Action | undefined> {
  const actions = await manager.listActions();
  return actions[actionRef];
}
