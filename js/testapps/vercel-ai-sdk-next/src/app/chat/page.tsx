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

'use client';

/**
 * useChat demo
 *
 * Server: src/app/api/chat/route.ts  →  chatHandler(chatFlow)
 * Flow:   src/genkit/chat.ts         →  MessagesSchema + StreamChunkSchema
 *
 * AI SDK v6 / @ai-sdk/react v3 API:
 *   - Input state is managed manually (no handleInputChange/handleSubmit).
 *   - Use sendMessage({ text }) to submit a user turn.
 *   - Default transport is DefaultChatTransport → POST /api/chat.
 */

import { useChat } from '@ai-sdk/react';
import { useState } from 'react';

export default function ChatPage() {
  const [input, setInput] = useState('');
  const { messages, sendMessage, status } = useChat({
    api: '/api/chat',
  } as any);

  const isLoading = status === 'streaming' || status === 'submitted';

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput('');
    void sendMessage({ text });
  }

  return (
    <div className="container">
      <nav>
        <a href="/">← Home</a>
        <a href="/completion">useCompletion</a>
        <a href="/object">useObject</a>
      </nav>

      <h1>useChat demo</h1>
      <p>
        Backed by <code>chatHandler</code> + a Genkit flow using{' '}
        <code>MessagesSchema</code> and <code>StreamChunkSchema</code>.
      </p>

      <div className="messages">
        {messages.length === 0 && (
          <span style={{ color: '#aaa', fontSize: '0.9rem' }}>
            No messages yet — say something!
          </span>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`message ${m.role}`}>
            <span className="role">{m.role}</span>
            <span className="text">
              {m.parts
                .filter((p) => p.type === 'text')
                .map((p) => (p as { type: 'text'; text: string }).text)
                .join('')}
            </span>
          </div>
        ))}
        {isLoading && (
          <div className="message assistant">
            <span className="role">assistant</span>
            <span className="text" style={{ color: '#aaa' }}>
              Thinking…
            </span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
