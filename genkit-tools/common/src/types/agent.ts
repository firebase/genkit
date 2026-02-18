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
import { MessageSchema, ModelResponseChunkSchema } from './model';
import { PartSchema } from './parts';

/**
 * Zod schema for an artifact produced during a session.
 */
export const ArtifactSchema = z.object({
  /** Name identifies the artifact (e.g., "generated_code.go", "diagram.png"). */
  name: z.string().optional(),
  /** Parts contains the artifact content (text, media, etc.). */
  parts: z.array(PartSchema),
  /** Metadata contains additional artifact-specific data. */
  metadata: z.record(z.any()).optional(),
});
export type Artifact = z.infer<typeof ArtifactSchema>;

/**
 * Zod schema for snapshot event.
 */
export const SnapshotEventSchema = z.enum(['turnEnd', 'invocationEnd']);
export type SnapshotEvent = z.infer<typeof SnapshotEventSchema>;

/**
 * Zod schema for session state.
 */
export const SessionStateSchema = z.object({
  /** Conversation history (user/model exchanges). */
  messages: z.array(MessageSchema).optional(),
  /** User-defined state associated with this conversation. */
  custom: z.any().optional(),
  /** Named collections of parts produced during the conversation. */
  artifacts: z.array(ArtifactSchema).optional(),
  /** Input used for agent flows that require input variables. */
  inputVariables: z.any().optional(),
});
export type SessionState = z.infer<typeof SessionStateSchema>;

/**
 * Zod schema for agent flow input (per-turn).
 */
export const AgentFlowInputSchema = z.object({
  /** User's input messages for this turn. */
  messages: z.array(MessageSchema).optional(),
  /** Tool request parts to re-execute interrupted tools. */
  toolRestarts: z.array(PartSchema).optional(),
});
export type AgentFlowInput = z.infer<typeof AgentFlowInputSchema>;

/**
 * Zod schema for agent flow initialization.
 */
export const AgentFlowInitSchema = z.object({
  /** Loads state from a persisted snapshot. Mutually exclusive with state. */
  snapshotId: z.string().optional(),
  /** Direct state for the invocation. Mutually exclusive with snapshotId. */
  state: SessionStateSchema.optional(),
});
export type AgentFlowInit = z.infer<typeof AgentFlowInitSchema>;

/**
 * Zod schema for agent flow result.
 */
export const AgentFlowResultSchema = z.object({
  /** Last model response message from the conversation. */
  message: MessageSchema.optional(),
  /** Artifacts produced during the session. */
  artifacts: z.array(ArtifactSchema).optional(),
});
export type AgentFlowResult = z.infer<typeof AgentFlowResultSchema>;

/**
 * Zod schema for agent flow output.
 */
export const AgentFlowOutputSchema = z.object({
  /** ID of the snapshot created at the end of this invocation. */
  snapshotId: z.string().optional(),
  /** Final conversation state (only when client-managed). */
  state: SessionStateSchema.optional(),
  /** Last model response message from the conversation. */
  message: MessageSchema.optional(),
  /** Artifacts produced during the session. */
  artifacts: z.array(ArtifactSchema).optional(),
});
export type AgentFlowOutput = z.infer<typeof AgentFlowOutputSchema>;

/**
 * Zod schema for agent flow stream chunk.
 */
export const AgentFlowStreamChunkSchema = z.object({
  /** Generation tokens from the model. */
  modelChunk: ModelResponseChunkSchema.optional(),
  /** User-defined structured status information. */
  status: z.any().optional(),
  /** A newly produced artifact. */
  artifact: ArtifactSchema.optional(),
  /** ID of a snapshot that was just persisted. */
  snapshotId: z.string().optional(),
  /** Signals that the agent flow has finished processing the current input. */
  endTurn: z.boolean().optional(),
});
export type AgentFlowStreamChunk = z.infer<typeof AgentFlowStreamChunkSchema>;
