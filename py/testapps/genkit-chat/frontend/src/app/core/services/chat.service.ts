/**
 * Copyright 2026 Google LLC
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
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { effect, Injectable, inject, signal } from '@angular/core';
import { catchError, type Observable, of } from 'rxjs';
import { PreferencesService } from './preferences.service';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
  model?: string;
  isError?: boolean;
  errorDetails?: string;
}

export interface ChatRequest {
  message: string;
  model: string;
  history?: { role: string; content: string }[];
}

export interface ChatResponse {
  response: string;
  model: string;
  latency_ms: number;
  isError?: boolean;
  errorDetails?: string;
}

export interface CompareRequest {
  prompt: string;
  models: string[];
}

export interface CompareResponse {
  prompt: string;
  responses: {
    model: string;
    response: string | null;
    latency_ms: number;
    error: string | null;
  }[];
}

export interface QueuedPrompt {
  id: string;
  content: string;
  model: string;
  timestamp: Date;
}

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private http = inject(HttpClient);
  private preferencesService = inject(PreferencesService);
  private apiUrl = '/api';

  messages = signal<Message[]>([]);
  isLoading = signal(false);

  // Prompt queue
  promptQueue = signal<QueuedPrompt[]>([]);
  private isProcessingQueue = false;

  // Streaming mode (load from preferences)
  streamingMode = signal(this.preferencesService.streamingMode);

  // Markdown rendering mode (load from preferences)
  markdownMode = signal(this.preferencesService.markdownMode);

  constructor() {
    // Persist streaming mode changes
    effect(() => {
      this.preferencesService.setStreamingMode(this.streamingMode());
    });

    // Persist markdown mode changes
    effect(() => {
      this.preferencesService.setMarkdownMode(this.markdownMode());
    });
  }

  sendMessage(message: string, model: string): Observable<ChatResponse> {
    const history = this.messages().map((m) => ({
      role: m.role,
      content: m.content,
    }));

    // Add user message to history immediately
    this.messages.update((msgs) => [
      ...msgs,
      { role: 'user', content: message, timestamp: new Date() },
    ]);

    this.isLoading.set(true);

    return this.http
      .post<ChatResponse>(`${this.apiUrl}/chat`, {
        message,
        model,
        history,
      })
      .pipe(
        catchError((error) => {
          const errorMessage =
            error?.error?.detail || error?.error?.message || error?.message || 'Unknown error';
          const errorDetails = JSON.stringify(error, null, 2);
          return of({
            response: `Error: ${errorMessage}`,
            model,
            latency_ms: 0,
            isError: true,
            errorDetails,
          });
        })
      );
  }

  addAssistantMessage(response: ChatResponse): void {
    this.messages.update((msgs) => [
      ...msgs,
      {
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        model: response.model,
        isError: response.isError,
        errorDetails: response.errorDetails,
      },
    ]);
    this.isLoading.set(false);
    // Process next queued prompt if any
    this.processNextInQueue();
  }

  /**
   * Process the next item in the queue automatically after a response is received.
   */
  private processNextInQueue(): void {
    if (this.promptQueue().length > 0 && !this.isLoading()) {
      const next = this.promptQueue()[0];
      this.removeFromQueue(next.id);

      if (this.streamingMode()) {
        this.sendStreamMessage(next.content, next.model, () => {
          this.processNextInQueue();
        });
      } else {
        this.sendMessage(next.content, next.model).subscribe({
          next: (response) => this.addAssistantMessage(response),
          error: (_err) => {
            this.isLoading.set(false);
            this.processNextInQueue();
          },
        });
      }
    }
  }

  toggleStreamingMode(): void {
    this.streamingMode.update((v) => !v);
  }

  toggleMarkdownMode(): void {
    this.markdownMode.update((v) => !v);
  }

  // Send message with streaming (returns EventSource URL)
  sendStreamMessage(message: string, model: string, onComplete?: () => void): void {
    const history = this.messages().map((m) => ({
      role: m.role,
      content: m.content,
    }));

    // Add user message to history immediately
    this.messages.update((msgs) => [
      ...msgs,
      { role: 'user', content: message, timestamp: new Date() },
    ]);

    this.isLoading.set(true);

    // Add placeholder assistant message
    this.messages.update((msgs) => [
      ...msgs,
      { role: 'assistant', content: '', timestamp: new Date(), model },
    ]);

    const eventSource = new EventSource(
      `${this.apiUrl}/stream?message=${encodeURIComponent(message)}&model=${encodeURIComponent(model)}&history=${encodeURIComponent(JSON.stringify(history))}`
    );

    eventSource.onmessage = (event) => {
      if (event.data === '[DONE]') {
        eventSource.close();
        this.isLoading.set(false);
        onComplete?.();
        return;
      }

      try {
        const data = JSON.parse(event.data);
        if (data.chunk) {
          // Update the last message (assistant) with new content
          this.messages.update((msgs) => {
            const updated = [...msgs];
            const lastMsg = updated[updated.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
              lastMsg.content += data.chunk;
            }
            return updated;
          });
        }
      } catch {
        // Handle plain text chunks
        this.messages.update((msgs) => {
          const updated = [...msgs];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.content += event.data;
          }
          return updated;
        });
      }
    };

    eventSource.onerror = (error) => {
      eventSource.close();
      this.messages.update((msgs) => {
        const updated = [...msgs];
        const lastMsg = updated[updated.length - 1];
        if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
          lastMsg.content = 'Error: Stream connection failed';
          lastMsg.isError = true;
          lastMsg.errorDetails = JSON.stringify(error, null, 2);
        }
        return updated;
      });
      this.isLoading.set(false);
      onComplete?.();
    };
  }

  compareModels(prompt: string, models: string[]): Observable<CompareResponse> {
    return this.http.post<CompareResponse>(`${this.apiUrl}/compare`, {
      prompt,
      models,
    });
  }

  clearHistory(): void {
    this.messages.set([]);
  }

  // Queue management methods
  addToQueue(content: string, model: string): void {
    const queuedPrompt: QueuedPrompt = {
      id: crypto.randomUUID(),
      content,
      model,
      timestamp: new Date(),
    };
    this.promptQueue.update((queue) => [...queue, queuedPrompt]);
    // Note: Don't process here - queue items are added when model is busy
    // Processing happens when the current request completes via addAssistantMessage
  }

  removeFromQueue(id: string): void {
    this.promptQueue.update((queue) => queue.filter((p) => p.id !== id));
  }

  clearQueue(): void {
    this.promptQueue.set([]);
  }

  sendFromQueue(id: string): void {
    const item = this.promptQueue().find((p) => p.id === id);
    if (!item || this.isLoading()) return;

    this.removeFromQueue(id);
    this.sendMessage(item.content, item.model).subscribe({
      next: (response) => this.addAssistantMessage(response),
      error: (_err) => {},
    });
  }

  sendAllFromQueue(): void {
    // Move all queue items to be processed - they will be sent sequentially
    // as the processNextInQueue is called after each response
    // For now, just start processing the first one if not already loading
    if (!this.isLoading() && this.promptQueue().length > 0) {
      const first = this.promptQueue()[0];
      this.sendFromQueue(first.id);
    }
  }

  updateQueuedPrompt(id: string, content: string): void {
    this.promptQueue.update((queue) => queue.map((p) => (p.id === id ? { ...p, content } : p)));
  }

  moveQueuedPromptUp(id: string): void {
    this.promptQueue.update((queue) => {
      const index = queue.findIndex((p) => p.id === id);
      if (index > 0) {
        const newQueue = [...queue];
        [newQueue[index - 1], newQueue[index]] = [newQueue[index], newQueue[index - 1]];
        return newQueue;
      }
      return queue;
    });
  }

  moveQueuedPromptDown(id: string): void {
    this.promptQueue.update((queue) => {
      const index = queue.findIndex((p) => p.id === id);
      if (index >= 0 && index < queue.length - 1) {
        const newQueue = [...queue];
        [newQueue[index], newQueue[index + 1]] = [newQueue[index + 1], newQueue[index]];
        return newQueue;
      }
      return queue;
    });
  }

  private processQueue(): void {
    if (this.isProcessingQueue || this.isLoading() || this.promptQueue().length === 0) {
      return;
    }

    this.isProcessingQueue = true;
    const [nextPrompt, ...remaining] = this.promptQueue();
    this.promptQueue.set(remaining);

    // Process the prompt
    this.sendMessage(nextPrompt.content, nextPrompt.model).subscribe({
      next: (response) => {
        this.addAssistantMessage(response);
        this.isProcessingQueue = false;
        // Process next in queue
        this.processQueue();
      },
      error: () => {
        this.isProcessingQueue = false;
        this.processQueue();
      },
    });
  }
}
