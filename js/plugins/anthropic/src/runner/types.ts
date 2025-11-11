/**
 * Original work Copyright 2024 Bloom Labs Inc
 * Modifications Copyright 2025 Google LLC
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

/**
 * Type constraint for runner type parameters.
 */
type RunnerTypes = {
  Message: unknown;
  Stream: AsyncIterable<unknown> & { finalMessage(): Promise<unknown> };
  StreamEvent: unknown;
  RequestBody: unknown;
  StreamingRequestBody: unknown;
  Tool: unknown;
  MessageParam: unknown;
  ContentBlockParam: unknown;
  ToolResponseContent: unknown;
};

type RunnerMessage<T extends RunnerTypes> = T['Message'];
type RunnerStream<T extends RunnerTypes> = T['Stream'];
type RunnerStreamEvent<T extends RunnerTypes> = T['StreamEvent'];
type RunnerRequestBody<T extends RunnerTypes> = T['RequestBody'];
type RunnerStreamingRequestBody<T extends RunnerTypes> =
  T['StreamingRequestBody'];
type RunnerTool<T extends RunnerTypes> = T['Tool'];
type RunnerMessageParam<T extends RunnerTypes> = T['MessageParam'];
type RunnerContentBlockParam<T extends RunnerTypes> = T['ContentBlockParam'];
type RunnerToolResponseContent<T extends RunnerTypes> =
  T['ToolResponseContent'];

export {
  RunnerContentBlockParam,
  RunnerMessage,
  RunnerMessageParam,
  RunnerRequestBody,
  RunnerStream,
  RunnerStreamEvent,
  RunnerStreamingRequestBody,
  RunnerTool,
  RunnerToolResponseContent,
  RunnerTypes,
};
