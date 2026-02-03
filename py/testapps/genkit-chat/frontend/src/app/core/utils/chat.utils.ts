// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

/**
 * Pure utility functions for chat operations.
 * These functions have no Angular dependencies and are easily testable.
 */

import type { Message, QueuedPrompt } from '../services/chat.service';

/**
 * Maximum number of items allowed in the prompt queue.
 */
export const MAX_QUEUE_SIZE = 50;

/**
 * Add a prompt to the queue.
 */
export function addToQueue(queue: QueuedPrompt[], content: string, model: string): QueuedPrompt[] {
  const newPrompt: QueuedPrompt = {
    id: crypto.randomUUID(),
    content,
    model,
    timestamp: new Date(),
  };
  return [...queue, newPrompt].slice(0, MAX_QUEUE_SIZE);
}

/**
 * Remove a prompt from the queue by ID.
 */
export function removeFromQueue(queue: QueuedPrompt[], id: string): QueuedPrompt[] {
  return queue.filter((p) => p.id !== id);
}

/**
 * Update a prompt's content in the queue.
 */
export function updateQueuedPrompt(
  queue: QueuedPrompt[],
  id: string,
  content: string
): QueuedPrompt[] {
  return queue.map((p) => (p.id === id ? { ...p, content } : p));
}

/**
 * Move a prompt up in the queue.
 */
export function moveQueuedPromptUp(queue: QueuedPrompt[], id: string): QueuedPrompt[] {
  const index = queue.findIndex((p) => p.id === id);
  if (index <= 0) return queue;

  const newQueue = [...queue];
  [newQueue[index - 1], newQueue[index]] = [newQueue[index], newQueue[index - 1]];
  return newQueue;
}

/**
 * Move a prompt down in the queue.
 */
export function moveQueuedPromptDown(queue: QueuedPrompt[], id: string): QueuedPrompt[] {
  const index = queue.findIndex((p) => p.id === id);
  if (index < 0 || index >= queue.length - 1) return queue;

  const newQueue = [...queue];
  [newQueue[index], newQueue[index + 1]] = [newQueue[index + 1], newQueue[index]];
  return newQueue;
}

/**
 * Get the first prompt from the queue and return the updated queue.
 */
export function popFromQueue(queue: QueuedPrompt[]): {
  prompt: QueuedPrompt | undefined;
  remaining: QueuedPrompt[];
} {
  if (queue.length === 0) {
    return { prompt: undefined, remaining: [] };
  }
  const [prompt, ...remaining] = queue;
  return { prompt, remaining };
}

/**
 * Build chat history from messages for API requests.
 */
export function buildHistory(messages: Message[]): Array<{ role: string; content: string }> {
  return messages.map((m) => ({
    role: m.role,
    content: m.content,
  }));
}

/**
 * Create a user message.
 */
export function createUserMessage(content: string): Message {
  return {
    role: 'user',
    content,
    timestamp: new Date(),
  };
}

/**
 * Create an assistant message from a response.
 */
export function createAssistantMessage(
  content: string,
  model: string,
  isError = false,
  errorDetails?: string
): Message {
  return {
    role: 'assistant',
    content,
    timestamp: new Date(),
    model,
    isError,
    errorDetails,
  };
}
