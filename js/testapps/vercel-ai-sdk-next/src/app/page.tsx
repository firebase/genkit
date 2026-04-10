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

export default function Home() {
  return (
    <div className="container">
      <h1>@genkit-ai/vercel-ai-sdk demos</h1>
      <p>
        These demos show how to use Genkit flows as backends for the Vercel AI SDK
        UI hooks. Each page has a live demo and links to the relevant source files.
      </p>
      <p>
        Set <code>GEMINI_API_KEY</code> before running{' '}
        <code>pnpm dev</code>.
      </p>

      <nav>
        <a href="/chat">useChat</a>
        <a href="/completion">useCompletion</a>
        <a href="/object">useObject</a>
      </nav>

      <h2>How it works</h2>
      <p>
        <strong>chatHandler</strong> — wraps a Genkit flow that uses{' '}
        <code>MessagesSchema</code> as <code>inputSchema</code> and{' '}
        <code>AiSdkChunkSchema</code> as <code>streamSchema</code>. Converts
        UIMessage history on every request and streams all Vercel AI SDK
        data-stream event types (text, reasoning, tools, citations, step
        markers, custom data).
      </p>
      <p>
        <strong>completionHandler</strong> — wraps a flow with{' '}
        <code>inputSchema: z.string()</code>. Reads the <code>prompt</code>{' '}
        field and streams plain text deltas or rich chunks. Supports both SSE
        and <code>streamProtocol: &apos;text&apos;</code> mode.
      </p>
      <p>
        <strong>objectHandler</strong> — wraps a flow that streams raw JSON
        text fragments. <code>useObject</code> reassembles them into a typed
        partial object in real time.
      </p>
    </div>
  );
}
