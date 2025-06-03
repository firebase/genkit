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

import { GenkitError } from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import { GenerateResponse } from './generate';
import { GenerateRequest, ModelAction, Operation } from './model';

export async function checkOperation(
  registry: Registry,
  operation: Operation
): Promise<Operation> {
  if (!operation.request || !operation.request?.model) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: 'Provided operation is missing original request information',
    });
  }
  const model = (await registry.lookupAction(
    `/model/${operation.request?.model}`
  )) as ModelAction;
  if (!model) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: `Failed to resolve model from original request: ${operation.request?.model}`,
    });
  }
  const request = {
    operation,
    messages: [],
  } as GenerateRequest;
  const rawResponse = await model(request);
  if (!rawResponse.model) {
    rawResponse.model = operation.request.model;
  }
  if (!rawResponse.operation) {
    throw new GenkitError({
      status: 'FAILED_PRECONDITION',
      message: `The model did not return expected operation information: ${JSON.stringify(rawResponse)}`,
    });
  }
  const response = new GenerateResponse(rawResponse, {
    request,
  });
  return response.operation!;
}
