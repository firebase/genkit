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

/**
 * Maps StreamChunk union values (and plain strings for backward-compat) to
 * `UIMessageStreamWriter.write()` calls, tracking which text/reasoning blocks
 * are currently open.
 */

import type { UIMessageStreamWriter } from 'ai';
import { StreamChunkSchema, type StreamChunk } from './schema.js';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

export interface DispatchState {
  openTextId: string | null;
  openReasoningId: string | null;
  /** Tool call IDs for which tool-input-start has been written. */
  openToolCallIds: Set<string>;
}

export function createDispatchState(): DispatchState {
  return {
    openTextId: null,
    openReasoningId: null,
    openToolCallIds: new Set(),
  };
}

// ---------------------------------------------------------------------------
// Main dispatch
// ---------------------------------------------------------------------------

/**
 * Dispatch a single `StreamChunk` from a flow's stream to the AI SDK
 * `UIMessageStreamWriter`. Unknown shapes are silently dropped.
 */
export function dispatchChunk(
  writer: UIMessageStreamWriter,
  rawChunk: unknown,
  state: DispatchState
): void {
  const parsed = StreamChunkSchema.safeParse(rawChunk);
  if (!parsed.success) return;
  const chunk: StreamChunk = parsed.data;

  switch (chunk.type) {
    case 'text': {
      if (!chunk.delta) return;
      ensureTextOpen(writer, state);
      writer.write({
        type: 'text-delta',
        id: state.openTextId!,
        delta: chunk.delta,
      });
      break;
    }

    case 'reasoning': {
      if (!chunk.delta) return;
      closeTextBlock(writer, state);
      ensureReasoningOpen(writer, state);
      writer.write({
        type: 'reasoning-delta',
        id: state.openReasoningId!,
        delta: chunk.delta,
      });
      break;
    }

    case 'tool-request': {
      closeTextBlock(writer, state);
      closeReasoningBlock(writer, state);
      const { toolCallId, toolName } = chunk;
      if (!state.openToolCallIds.has(toolCallId)) {
        state.openToolCallIds.add(toolCallId);
        writer.write({ type: 'tool-input-start', toolCallId, toolName });
      }
      if (chunk.inputDelta !== undefined) {
        writer.write({
          type: 'tool-input-delta',
          toolCallId,
          inputTextDelta: chunk.inputDelta,
        });
      } else if (chunk.input !== undefined) {
        writer.write({
          type: 'tool-input-available',
          toolCallId,
          toolName,
          input: chunk.input,
        });
        state.openToolCallIds.delete(toolCallId);
      }
      break;
    }

    case 'tool-result': {
      writer.write({
        type: 'tool-output-available',
        toolCallId: chunk.toolCallId,
        output: chunk.output,
      });
      break;
    }

    case 'file': {
      writer.write({
        type: 'file',
        url: chunk.url,
        mediaType: chunk.mediaType,
      });
      break;
    }

    case 'source-url': {
      writer.write({
        type: 'source-url',
        sourceId: chunk.sourceId,
        url: chunk.url,
        ...(chunk.title ? { title: chunk.title } : {}),
      });
      break;
    }

    case 'source-document': {
      writer.write({
        type: 'source-document',
        sourceId: chunk.sourceId,
        mediaType: chunk.mediaType,
        title: chunk.title,
        ...(chunk.filename ? { filename: chunk.filename } : {}),
      });
      break;
    }

    case 'data': {
      // The AI SDK writer types `data-*` events via `z.custom<\`data-${string}\`>()`,
      // which TypeScript cannot express as a literal template type on the write() overload.
      // The cast is safe: any `data-${string}` value is accepted at runtime.
      writer.write({
        type: `data-${chunk.id}` as `data-${string}`,
        data: chunk.value,
      });
      break;
    }

    case 'step-start': {
      closeTextBlock(writer, state);
      closeReasoningBlock(writer, state);
      writer.write({ type: 'start-step' });
      break;
    }

    case 'step-end': {
      closeOpenBlocks(writer, state);
      writer.write({ type: 'finish-step' });
      break;
    }
  }
}

// ---------------------------------------------------------------------------
// Block state helpers (exported so callers can close blocks at stream end)
// ---------------------------------------------------------------------------

export function closeOpenBlocks(
  writer: UIMessageStreamWriter,
  state: DispatchState
): void {
  closeTextBlock(writer, state);
  closeReasoningBlock(writer, state);
}

function ensureTextOpen(
  writer: UIMessageStreamWriter,
  state: DispatchState
): void {
  closeReasoningBlock(writer, state);
  if (!state.openTextId) {
    state.openTextId = globalThis.crypto.randomUUID();
    writer.write({ type: 'text-start', id: state.openTextId });
  }
}

function ensureReasoningOpen(
  writer: UIMessageStreamWriter,
  state: DispatchState
): void {
  if (!state.openReasoningId) {
    state.openReasoningId = globalThis.crypto.randomUUID();
    writer.write({ type: 'reasoning-start', id: state.openReasoningId });
  }
}

function closeTextBlock(
  writer: UIMessageStreamWriter,
  state: DispatchState
): void {
  if (state.openTextId) {
    writer.write({ type: 'text-end', id: state.openTextId });
    state.openTextId = null;
  }
}

function closeReasoningBlock(
  writer: UIMessageStreamWriter,
  state: DispatchState
): void {
  if (state.openReasoningId) {
    writer.write({ type: 'reasoning-end', id: state.openReasoningId });
    state.openReasoningId = null;
  }
}
