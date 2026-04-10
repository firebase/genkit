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
 * useObject demo
 *
 * Server: src/app/api/object/route.ts  →  objectHandler(notificationsFlow)
 * Flow:   src/genkit/object.ts          →  { topic } input + z.string() stream
 *
 * The objectHandler adapter streams raw JSON text fragments.  useObject
 * reassembles them incrementally using the provided Zod schema, updating
 * `object` as each fragment arrives.  The UI renders partial data in real time.
 *
 * Note: errors that happen mid-stream cannot be surfaced cleanly to the client
 * because the useObject protocol uses raw text/plain with no error channel.
 * Pre-stream errors (auth failures, bad input) still return a non-2xx status.
 */

import { experimental_useObject as useObject } from '@ai-sdk/react';
import { useState } from 'react';
import { NotificationsSchema, type Notification } from '@/lib/schemas';

export default function ObjectPage() {
  const [topic, setTopic] = useState('');

  const { object, submit, isLoading } = useObject({
    api: '/api/object',
    schema: NotificationsSchema,
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (topic.trim()) submit({ topic: topic.trim() });
  }

  return (
    <div className="container">
      <nav>
        <a href="/">← Home</a>
        <a href="/chat">useChat</a>
        <a href="/completion">useCompletion</a>
      </nav>

      <h1>useObject demo</h1>
      <p>
        Backed by <code>objectHandler</code> + a Genkit flow that streams raw
        JSON fragments. <code>useObject</code> reassembles them incrementally —
        cards appear and fill in as the stream arrives.
      </p>

      <form onSubmit={handleSubmit} className="input-row">
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Notification topic (e.g. weather, fitness, news)…"
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !topic.trim()}>
          {isLoading ? 'Generating…' : 'Generate'}
        </button>
      </form>

      {object?.notifications && object.notifications.length > 0 ? (
        <div className="cards">
          {object.notifications.map((n: Partial<Notification> | undefined, i: number) => (
            <div key={i} className="card">
              <span className="icon">{n?.icon ?? '🔔'}</span>
              <div className="card-body">
                <div className="card-title">{n?.title ?? '…'}</div>
                <div className="card-text">{n?.body ?? ''}</div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        !isLoading && (
          <p className="status">Enter a topic and click Generate.</p>
        )
      )}

      {isLoading && (
        <p className="status">Generating notifications…</p>
      )}
    </div>
  );
}
