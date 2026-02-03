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

import { describe, expect, it, vi } from 'vitest';
import type { Message, QueuedPrompt } from '../services/chat.service';
import {
  addToQueue,
  buildHistory,
  createAssistantMessage,
  createUserMessage,
  MAX_QUEUE_SIZE,
  moveQueuedPromptDown,
  moveQueuedPromptUp,
  popFromQueue,
  removeFromQueue,
  updateQueuedPrompt,
} from './chat.utils';

// Mock crypto.randomUUID
vi.stubGlobal('crypto', {
  randomUUID: () => `test-uuid-${Math.random().toString(36).slice(2, 9)}`,
});

describe('chat.utils', () => {
  describe('addToQueue', () => {
    it('should add a prompt to empty queue', () => {
      const result = addToQueue([], 'Hello', 'model-1');
      expect(result).toHaveLength(1);
      expect(result[0].content).toBe('Hello');
      expect(result[0].model).toBe('model-1');
    });

    it('should add a prompt to existing queue', () => {
      const existing: QueuedPrompt[] = [
        { id: '1', content: 'First', model: 'model-1', timestamp: new Date() },
      ];
      const result = addToQueue(existing, 'Second', 'model-2');
      expect(result).toHaveLength(2);
      expect(result[1].content).toBe('Second');
    });

    it('should limit queue to MAX_QUEUE_SIZE', () => {
      const queue: QueuedPrompt[] = Array.from({ length: MAX_QUEUE_SIZE }, (_, i) => ({
        id: `${i}`,
        content: `Prompt ${i}`,
        model: 'model',
        timestamp: new Date(),
      }));
      const result = addToQueue(queue, 'Overflow', 'model');
      expect(result).toHaveLength(MAX_QUEUE_SIZE);
    });

    it('should generate unique IDs', () => {
      const result1 = addToQueue([], 'First', 'model');
      const result2 = addToQueue([], 'Second', 'model');
      expect(result1[0].id).not.toBe(result2[0].id);
    });
  });

  describe('removeFromQueue', () => {
    const queue: QueuedPrompt[] = [
      { id: '1', content: 'First', model: 'model', timestamp: new Date() },
      { id: '2', content: 'Second', model: 'model', timestamp: new Date() },
      { id: '3', content: 'Third', model: 'model', timestamp: new Date() },
    ];

    it('should remove a prompt by ID', () => {
      const result = removeFromQueue(queue, '2');
      expect(result).toHaveLength(2);
      expect(result.find((p) => p.id === '2')).toBeUndefined();
    });

    it('should return same array if ID not found', () => {
      const result = removeFromQueue(queue, 'nonexistent');
      expect(result).toHaveLength(3);
    });

    it('should handle empty queue', () => {
      const result = removeFromQueue([], '1');
      expect(result).toHaveLength(0);
    });
  });

  describe('updateQueuedPrompt', () => {
    const queue: QueuedPrompt[] = [
      { id: '1', content: 'Original', model: 'model', timestamp: new Date() },
    ];

    it('should update content by ID', () => {
      const result = updateQueuedPrompt(queue, '1', 'Updated');
      expect(result[0].content).toBe('Updated');
    });

    it('should not modify other fields', () => {
      const result = updateQueuedPrompt(queue, '1', 'Updated');
      expect(result[0].model).toBe('model');
      expect(result[0].id).toBe('1');
    });

    it('should not change array if ID not found', () => {
      const result = updateQueuedPrompt(queue, 'nonexistent', 'Updated');
      expect(result[0].content).toBe('Original');
    });
  });

  describe('moveQueuedPromptUp', () => {
    const queue: QueuedPrompt[] = [
      { id: '1', content: 'First', model: 'model', timestamp: new Date() },
      { id: '2', content: 'Second', model: 'model', timestamp: new Date() },
      { id: '3', content: 'Third', model: 'model', timestamp: new Date() },
    ];

    it('should move prompt up', () => {
      const result = moveQueuedPromptUp(queue, '2');
      expect(result[0].id).toBe('2');
      expect(result[1].id).toBe('1');
    });

    it('should not move first item', () => {
      const result = moveQueuedPromptUp(queue, '1');
      expect(result[0].id).toBe('1');
    });

    it('should not modify if ID not found', () => {
      const result = moveQueuedPromptUp(queue, 'nonexistent');
      expect(result).toEqual(queue);
    });
  });

  describe('moveQueuedPromptDown', () => {
    const queue: QueuedPrompt[] = [
      { id: '1', content: 'First', model: 'model', timestamp: new Date() },
      { id: '2', content: 'Second', model: 'model', timestamp: new Date() },
      { id: '3', content: 'Third', model: 'model', timestamp: new Date() },
    ];

    it('should move prompt down', () => {
      const result = moveQueuedPromptDown(queue, '2');
      expect(result[1].id).toBe('3');
      expect(result[2].id).toBe('2');
    });

    it('should not move last item', () => {
      const result = moveQueuedPromptDown(queue, '3');
      expect(result[2].id).toBe('3');
    });

    it('should not modify if ID not found', () => {
      const result = moveQueuedPromptDown(queue, 'nonexistent');
      expect(result).toEqual(queue);
    });
  });

  describe('popFromQueue', () => {
    it('should pop first item from queue', () => {
      const queue: QueuedPrompt[] = [
        { id: '1', content: 'First', model: 'model', timestamp: new Date() },
        { id: '2', content: 'Second', model: 'model', timestamp: new Date() },
      ];
      const { prompt, remaining } = popFromQueue(queue);
      expect(prompt?.id).toBe('1');
      expect(remaining).toHaveLength(1);
      expect(remaining[0].id).toBe('2');
    });

    it('should handle empty queue', () => {
      const { prompt, remaining } = popFromQueue([]);
      expect(prompt).toBeUndefined();
      expect(remaining).toHaveLength(0);
    });
  });

  describe('buildHistory', () => {
    it('should build history from messages', () => {
      const messages: Message[] = [
        { role: 'user', content: 'Hello' },
        { role: 'assistant', content: 'Hi!' },
      ];
      const history = buildHistory(messages);
      expect(history).toHaveLength(2);
      expect(history[0]).toEqual({ role: 'user', content: 'Hello' });
    });

    it('should strip extra fields', () => {
      const messages: Message[] = [
        { role: 'user', content: 'Hello', timestamp: new Date(), model: 'test' },
      ];
      const history = buildHistory(messages);
      expect(history[0]).toEqual({ role: 'user', content: 'Hello' });
    });
  });

  describe('createUserMessage', () => {
    it('should create a user message', () => {
      const message = createUserMessage('Hello');
      expect(message.role).toBe('user');
      expect(message.content).toBe('Hello');
      expect(message.timestamp).toBeInstanceOf(Date);
    });
  });

  describe('createAssistantMessage', () => {
    it('should create an assistant message', () => {
      const message = createAssistantMessage('Response', 'model-1');
      expect(message.role).toBe('assistant');
      expect(message.content).toBe('Response');
      expect(message.model).toBe('model-1');
    });

    it('should handle error messages', () => {
      const message = createAssistantMessage('Error', 'model-1', true, '{"code": 500}');
      expect(message.isError).toBe(true);
      expect(message.errorDetails).toBe('{"code": 500}');
    });
  });
});
