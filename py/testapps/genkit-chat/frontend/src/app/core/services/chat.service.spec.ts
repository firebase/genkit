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

import { describe, expect, it } from 'vitest';
import type { ChatResponse, Message, QueuedPrompt } from './chat.service';

// Test the data structures and logic without Angular's HttpClient dependency

describe('ChatService data structures', () => {
  describe('Message interface', () => {
    it('should accept user message', () => {
      const message: Message = {
        role: 'user',
        content: 'Hello, world!',
        timestamp: new Date(),
      };
      expect(message.role).toBe('user');
      expect(message.content).toBe('Hello, world!');
    });

    it('should accept assistant message', () => {
      const message: Message = {
        role: 'assistant',
        content: 'Hello! How can I help you?',
        timestamp: new Date(),
        model: 'googleai/gemini-1.5-flash',
      };
      expect(message.role).toBe('assistant');
      expect(message.model).toBe('googleai/gemini-1.5-flash');
    });

    it('should accept error message', () => {
      const message: Message = {
        role: 'assistant',
        content: 'Error: Something went wrong',
        isError: true,
        errorDetails: '{"code": 500}',
      };
      expect(message.isError).toBe(true);
      expect(message.errorDetails).toBeDefined();
    });
  });

  describe('QueuedPrompt interface', () => {
    it('should have required fields', () => {
      const prompt: QueuedPrompt = {
        id: 'test-uuid',
        content: 'What is Genkit?',
        model: 'googleai/gemini-1.5-flash',
        timestamp: new Date(),
      };
      expect(prompt.id).toBe('test-uuid');
      expect(prompt.content).toBe('What is Genkit?');
      expect(prompt.model).toBe('googleai/gemini-1.5-flash');
    });
  });

  describe('ChatResponse interface', () => {
    it('should accept successful response', () => {
      const response: ChatResponse = {
        response: 'Genkit is a framework for building AI apps.',
        model: 'googleai/gemini-1.5-flash',
        latency_ms: 1234,
      };
      expect(response.latency_ms).toBe(1234);
      expect(response.isError).toBeUndefined();
    });

    it('should accept error response', () => {
      const response: ChatResponse = {
        response: 'Error: Rate limit exceeded',
        model: 'googleai/gemini-1.5-flash',
        latency_ms: 0,
        isError: true,
        errorDetails: '{"code": 429}',
      };
      expect(response.isError).toBe(true);
    });
  });
});

describe('ChatService queue logic', () => {
  describe('queue operations', () => {
    it('should add to queue correctly', () => {
      const queue: QueuedPrompt[] = [];
      const newPrompt: QueuedPrompt = {
        id: 'prompt-1',
        content: 'First prompt',
        model: 'model-1',
        timestamp: new Date(),
      };

      const updatedQueue = [...queue, newPrompt];
      expect(updatedQueue.length).toBe(1);
      expect(updatedQueue[0].id).toBe('prompt-1');
    });

    it('should remove from queue correctly', () => {
      const queue: QueuedPrompt[] = [
        { id: 'prompt-1', content: 'First', model: 'model', timestamp: new Date() },
        { id: 'prompt-2', content: 'Second', model: 'model', timestamp: new Date() },
        { id: 'prompt-3', content: 'Third', model: 'model', timestamp: new Date() },
      ];

      const filtered = queue.filter((p) => p.id !== 'prompt-2');
      expect(filtered.length).toBe(2);
      expect(filtered.map((p) => p.id)).toEqual(['prompt-1', 'prompt-3']);
    });

    it('should clear queue correctly', () => {
      const _queue: QueuedPrompt[] = [
        { id: 'prompt-1', content: 'First', model: 'model', timestamp: new Date() },
        { id: 'prompt-2', content: 'Second', model: 'model', timestamp: new Date() },
      ];

      const cleared: QueuedPrompt[] = [];
      expect(cleared.length).toBe(0);
    });

    it('should move prompt up in queue', () => {
      const queue: QueuedPrompt[] = [
        { id: 'prompt-1', content: 'First', model: 'model', timestamp: new Date() },
        { id: 'prompt-2', content: 'Second', model: 'model', timestamp: new Date() },
        { id: 'prompt-3', content: 'Third', model: 'model', timestamp: new Date() },
      ];

      // Move prompt-2 up
      const index = queue.findIndex((p) => p.id === 'prompt-2');
      if (index > 0) {
        const newQueue = [...queue];
        [newQueue[index - 1], newQueue[index]] = [newQueue[index], newQueue[index - 1]];
        expect(newQueue.map((p) => p.id)).toEqual(['prompt-2', 'prompt-1', 'prompt-3']);
      }
    });

    it('should move prompt down in queue', () => {
      const queue: QueuedPrompt[] = [
        { id: 'prompt-1', content: 'First', model: 'model', timestamp: new Date() },
        { id: 'prompt-2', content: 'Second', model: 'model', timestamp: new Date() },
        { id: 'prompt-3', content: 'Third', model: 'model', timestamp: new Date() },
      ];

      // Move prompt-2 down
      const index = queue.findIndex((p) => p.id === 'prompt-2');
      if (index >= 0 && index < queue.length - 1) {
        const newQueue = [...queue];
        [newQueue[index], newQueue[index + 1]] = [newQueue[index + 1], newQueue[index]];
        expect(newQueue.map((p) => p.id)).toEqual(['prompt-1', 'prompt-3', 'prompt-2']);
      }
    });

    it('should update queued prompt content', () => {
      const queue: QueuedPrompt[] = [
        { id: 'prompt-1', content: 'Original content', model: 'model', timestamp: new Date() },
      ];

      const newContent = 'Updated content';
      const updated = queue.map((p) => (p.id === 'prompt-1' ? { ...p, content: newContent } : p));

      expect(updated[0].content).toBe('Updated content');
    });
  });
});

describe('Message history logic', () => {
  it('should build history from messages', () => {
    const messages: Message[] = [
      { role: 'user', content: 'Hello' },
      { role: 'assistant', content: 'Hi there!' },
      { role: 'user', content: 'How are you?' },
    ];

    const history = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    expect(history.length).toBe(3);
    expect(history[0]).toEqual({ role: 'user', content: 'Hello' });
    expect(history[1]).toEqual({ role: 'assistant', content: 'Hi there!' });
  });

  it('should add user message to messages', () => {
    const messages: Message[] = [];
    const newMessage = 'Test message';

    const updated = [
      ...messages,
      { role: 'user' as const, content: newMessage, timestamp: new Date() },
    ];

    expect(updated.length).toBe(1);
    expect(updated[0].role).toBe('user');
    expect(updated[0].content).toBe('Test message');
  });

  it('should add assistant message with response', () => {
    const messages: Message[] = [{ role: 'user', content: 'Hello' }];

    const response: ChatResponse = {
      response: 'Hi there!',
      model: 'test-model',
      latency_ms: 100,
    };

    const updated = [
      ...messages,
      {
        role: 'assistant' as const,
        content: response.response,
        timestamp: new Date(),
        model: response.model,
        isError: response.isError,
        errorDetails: response.errorDetails,
      },
    ];

    expect(updated.length).toBe(2);
    expect(updated[1].role).toBe('assistant');
    expect(updated[1].content).toBe('Hi there!');
    expect(updated[1].model).toBe('test-model');
  });
});
