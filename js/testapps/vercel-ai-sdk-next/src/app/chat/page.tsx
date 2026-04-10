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
 * Demonstrates:
 * - Text streaming via toStreamChunks()
 * - Tool calls: ask "What's the weather in Tokyo?" to trigger getWeather
 * - Custom data chunks: token usage displayed below each assistant message
 * - Reasoning parts (if the model emits extended thinking)
 */

import { useChat } from '@ai-sdk/react';
import { useState } from 'react';

type Part = { type: string; [key: string]: unknown };

function MessageParts({ parts }: { parts: Part[] }) {
  return (
    <>
      {parts.map((p, i) => {
        if (p.type === 'text') {
          return (
            <span key={i} style={{ whiteSpace: 'pre-wrap' }}>
              {p.text as string}
            </span>
          );
        }
        if (p.type === 'reasoning') {
          return (
            <details key={i} style={{ color: '#888', fontSize: '0.85rem' }}>
              <summary>Reasoning</summary>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                {p.reasoning as string}
              </pre>
            </details>
          );
        }
        if (p.type === 'tool-invocation') {
          const ti = p.toolInvocation as {
            toolName: string;
            state: string;
            args?: unknown;
            result?: unknown;
          };
          return (
            <div
              key={i}
              style={{
                fontFamily: 'monospace',
                fontSize: '0.8rem',
                background: '#f4f4f4',
                padding: '4px 8px',
                borderRadius: 4,
                margin: '2px 0',
              }}>
              <strong>{ti.toolName}</strong>
              {ti.state === 'result' ? (
                <>
                  ({JSON.stringify(ti.args)}) →{' '}
                  <span style={{ color: '#2a6' }}>
                    {JSON.stringify(ti.result)}
                  </span>
                </>
              ) : (
                <span style={{ color: '#aaa' }}> (calling…)</span>
              )}
            </div>
          );
        }
        return null;
      })}
    </>
  );
}

export default function ChatPage() {
  const [input, setInput] = useState('');
  const { messages, sendMessage, status, data } = useChat({
    api: '/api/chat',
  } as any);

  const isLoading = status === 'streaming' || status === 'submitted';

  // Latest usage data from custom `data` chunks emitted by the flow.
  const latestUsage = (data as unknown[])
    ?.filter(
      (d): d is { type: string; value: Record<string, number> } =>
        typeof d === 'object' &&
        d !== null &&
        (d as Record<string, unknown>).type === 'usage'
    )
    .at(-1)?.value;

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
        Backed by <code>chatHandler</code> + <code>StreamChunkSchema</code>.
        Try: <em>&ldquo;What&apos;s the weather in Tokyo?&rdquo;</em> to trigger
        a tool call.
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
              <MessageParts parts={m.parts as Part[]} />
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

      {latestUsage && (
        <p style={{ fontSize: '0.75rem', color: '#888', margin: '4px 0' }}>
          Tokens — in: {latestUsage.inputTokens ?? '?'} / out:{' '}
          {latestUsage.outputTokens ?? '?'}
        </p>
      )}

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
