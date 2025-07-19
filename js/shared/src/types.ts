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
import {
  CustomPartSchema,
  DataPartSchema,
  DocumentDataSchema,
  DocumentPartSchema,
  MediaPartSchema,
  MediaSchema,
  ReasoningPartSchema,
  TextPartSchema,
  ToolRequestPartSchema,
  ToolRequestSchema,
  ToolResponsePartSchema,
  ToolResponseSchema,
} from './__codegen/document.js';
import {
  EmbedRequestSchema,
  EmbedResponseSchema,
  EmbeddingSchema,
  type EmbeddingBatch,
} from './__codegen/embedder.js';
import {
  BaseDataPointSchema,
  BaseEvalDataPointSchema,
  EvalFnResponseSchema,
  EvalRequestSchema,
  EvalResponseSchema,
  EvalStatusEnumSchema,
  ScoreSchema,
} from './__codegen/evaluator.js';
import {
  CandidateErrorSchema,
  CandidateSchema,
  FinishReasonSchema,
  GenerateActionOptionsSchema,
  GenerateActionOutputConfig,
  GenerateRequestSchema,
  GenerateResponseChunkSchema,
  GenerateResponseSchema,
  GenerationCommonConfigDescriptions,
  GenerationCommonConfigSchema,
  GenerationUsageSchema,
  MessageSchema,
  ModelInfoSchema,
  ModelRequestSchema,
  ModelResponseChunkSchema,
  ModelResponseSchema,
  OperationSchema,
  OutputConfigSchema,
  PartSchema,
  RoleSchema,
  ToolDefinitionSchema,
} from './__codegen/model.js';
import {
  CommonRerankerOptionsSchema,
  RankedDocumentDataSchema,
  RankedDocumentMetadataSchema,
  RerankerRequestSchema,
  RerankerResponseSchema,
} from './__codegen/reranker.js';
import {
  CommonRetrieverOptionsSchema,
  RetrieverRequestSchema,
  RetrieverResponseSchema,
} from './__codegen/retriever.js';
import { Status, StatusCodes, StatusSchema } from './__codegen/status.js';

/**
 * Background operation.
 */
export interface Operation<O = any> {
  action?: string;
  id: string;
  done?: boolean;
  output?: O;
  error?: { message: string; [key: string]: unknown };
  metadata?: Record<string, any>;
}

/** @deprecated All responses now return a single candidate. Only the first candidate will be used if supplied. */
export type CandidateData = z.infer<typeof CandidateSchema>;

export type CustomPart = z.infer<typeof CustomPartSchema>;
export type DataPart = z.infer<typeof DataPartSchema>;
export type DocumentData = z.infer<typeof DocumentDataSchema>;
export type DocumentPart = z.infer<typeof DocumentPartSchema>;
export type MediaPart = z.infer<typeof MediaPartSchema>;
export type Media = z.infer<typeof MediaSchema>;
export type ReasoningPart = z.infer<typeof ReasoningPartSchema>;
export type TextPart = z.infer<typeof TextPartSchema>;
export type ToolRequestPart = z.infer<typeof ToolRequestPartSchema>;
export type ToolRequest = z.infer<typeof ToolRequestSchema>;
export type ToolResponsePart = z.infer<typeof ToolResponsePartSchema>;
export type ToolResponse = z.infer<typeof ToolResponseSchema>;
export type EmbedRequest = z.infer<typeof EmbedRequestSchema>;
export type EmbedResponse = z.infer<typeof EmbedResponseSchema>;
export type Embedding = z.infer<typeof EmbeddingSchema>;
export type BaseDataPoint = z.infer<typeof BaseDataPointSchema>;
export type BaseEvalDataPoint = z.infer<typeof BaseEvalDataPointSchema>;
export type EvalFnResponse = z.infer<typeof EvalFnResponseSchema>;
export type EvalRequest = z.infer<typeof EvalRequestSchema>;
export type EvalResponse = z.infer<typeof EvalResponseSchema>;
export type EvalStatusEnum = z.infer<typeof EvalStatusEnumSchema>;
export type Score = z.infer<typeof ScoreSchema>;
export type FinishReason = z.infer<typeof FinishReasonSchema>;
export type GenerateActionOptions = z.infer<typeof GenerateActionOptionsSchema>;
export type GenerateRequestData = z.infer<typeof GenerateRequestSchema>;

/**
 * Generate request.
 */
export interface GenerateRequest<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
> extends z.infer<typeof GenerateRequestSchema> {
  config?: z.infer<CustomOptionsSchema>;
}

export type GenerateResponseChunkData = z.infer<
  typeof GenerateResponseChunkSchema
>;
export type GenerateResponseData = z.infer<typeof GenerateResponseSchema>;
export type GenerationCommonConfig = z.infer<
  typeof GenerationCommonConfigSchema
>;
export type GenerationUsage = z.infer<typeof GenerationUsageSchema>;
export type MessageData = z.infer<typeof MessageSchema>;
export type ModelInfo = z.infer<typeof ModelInfoSchema>;

/** ModelRequest represents the parameters that are passed to a model when generating content. */
export interface ModelRequest<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
> extends z.infer<typeof ModelRequestSchema> {
  config?: z.infer<CustomOptionsSchema>;
}

export type ModelResponseChunkData = z.infer<typeof ModelResponseChunkSchema>;
export type ModelResponseData = z.infer<typeof ModelResponseSchema>;
export type OutputConfig = z.infer<typeof OutputConfigSchema>;
export type Part = z.infer<typeof PartSchema>;
export type Role = z.infer<typeof RoleSchema>;
export type ToolDefinition = z.infer<typeof ToolDefinitionSchema>;
export type CommonRerankerOptions = z.infer<typeof CommonRerankerOptionsSchema>;
export type RankedDocumentData = z.infer<typeof RankedDocumentDataSchema>;
export type RankedDocumentMetadata = z.infer<
  typeof RankedDocumentMetadataSchema
>;
export type RerankerRequest = z.infer<typeof RerankerRequestSchema>;
export type RerankerResponse = z.infer<typeof RerankerResponseSchema>;
export type CommonRetrieverOptions = z.infer<
  typeof CommonRetrieverOptionsSchema
>;
export type RetrieverRequest = z.infer<typeof RetrieverRequestSchema>;
export type RetrieverResponse = z.infer<typeof RetrieverResponseSchema>;

/** @deprecated All responses now return a single candidate. Only the first candidate will be used if supplied. */
export type CandidateError = z.infer<typeof CandidateErrorSchema>;

export {
  BaseDataPointSchema,
  BaseEvalDataPointSchema,
  CandidateErrorSchema,
  CandidateSchema,
  CommonRerankerOptionsSchema,
  CommonRetrieverOptionsSchema,
  CustomPartSchema,
  DataPartSchema,
  DocumentDataSchema,
  DocumentPartSchema,
  GenerationCommonConfigDescriptions,
  EmbedRequestSchema,
  EmbedResponseSchema,
  EmbeddingSchema,
  EvalFnResponseSchema,
  EvalRequestSchema,
  EvalResponseSchema,
  EvalStatusEnumSchema,
  FinishReasonSchema,
  GenerateActionOptionsSchema,
  GenerateActionOutputConfig,
  GenerateRequestSchema,
  GenerateResponseChunkSchema,
  GenerateResponseSchema,
  GenerationCommonConfigSchema,
  GenerationUsageSchema,
  MediaPartSchema,
  MediaSchema,
  MessageSchema,
  ModelInfoSchema,
  ModelRequestSchema,
  ModelResponseChunkSchema,
  ModelResponseSchema,
  OperationSchema,
  OutputConfigSchema,
  PartSchema,
  RankedDocumentDataSchema,
  RankedDocumentMetadataSchema,
  ReasoningPartSchema,
  RerankerRequestSchema,
  RerankerResponseSchema,
  RetrieverRequestSchema,
  RetrieverResponseSchema,
  RoleSchema,
  ScoreSchema,
  Status,
  StatusCodes,
  StatusSchema,
  TextPartSchema,
  ToolDefinitionSchema,
  ToolRequestPartSchema,
  ToolRequestSchema,
  ToolResponsePartSchema,
  ToolResponseSchema,
  type EmbeddingBatch,
};
