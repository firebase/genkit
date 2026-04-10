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
 * useCompletion demo
 *
 * Server: src/app/api/completion/route.ts  →  completionHandler(completionFlow)
 * Flow:   src/genkit/completion.ts          →  z.string() + z.string() stream
 *
 * useCompletion POSTs { prompt: string } to /api/completion and streams the
 * response text delta-by-delta.  The adapter wraps each delta in the Vercel
 * AI SDK data-stream SSE format.
 *
 * To switch to plain-text streaming:
 *   1. Add  streamProtocol: 'text'  to the useCompletion options below.
 *   2. Add  streamProtocol: 'text'  to completionHandler options in route.ts.
 */

import { useCompletion } from '@ai-sdk/react';

export default function CompletionPage() {
  const { completion, input, handleInputChange, handleSubmit, isLoading } =
    useCompletion({ api: '/api/completion' });

  return (
    <div className="container">
      <nav>
        <a href="/">← Home</a>
        <a href="/chat">useChat</a>
        <a href="/object">useObject</a>
      </nav>

      <h1>useCompletion demo</h1>
      <p>
        Backed by <code>completionHandler</code> + a Genkit flow with{' '}
        <code>inputSchema: z.string()</code>. Reads the <code>prompt</code>{' '}
        field and streams plain text deltas.
      </p>

      <form onSubmit={handleSubmit} className="input-row">
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="Enter a prompt…"
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          {isLoading ? 'Generating…' : 'Generate'}
        </button>
      </form>

      <div className="output">
        {completion || (
          <span style={{ color: '#aaa' }}>Output will appear here…</span>
        )}
      </div>
    </div>
  );
}
