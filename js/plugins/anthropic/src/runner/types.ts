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

type RunnerMessage<ApiTypes extends RunnerTypes> = ApiTypes['Message'];
type RunnerStream<ApiTypes extends RunnerTypes> = ApiTypes['Stream'];
type RunnerStreamEvent<ApiTypes extends RunnerTypes> = ApiTypes['StreamEvent'];
type RunnerRequestBody<ApiTypes extends RunnerTypes> = ApiTypes['RequestBody'];
type RunnerStreamingRequestBody<ApiTypes extends RunnerTypes> =
  ApiTypes['StreamingRequestBody'];
type RunnerTool<ApiTypes extends RunnerTypes> = ApiTypes['Tool'];
type RunnerMessageParam<ApiTypes extends RunnerTypes> =
  ApiTypes['MessageParam'];
type RunnerContentBlockParam<ApiTypes extends RunnerTypes> =
  ApiTypes['ContentBlockParam'];
type RunnerToolResponseContent<ApiTypes extends RunnerTypes> =
  ApiTypes['ToolResponseContent'];

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
