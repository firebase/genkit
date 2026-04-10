# @genkit-ai/vercel-ai-sdk

Adapter helpers that connect [Genkit](https://genkit.dev) streaming flows to the [Vercel AI SDK](https://sdk.vercel.ai) UI hooks: `useChat()`, `useCompletion()`, and `useObject()`.

Each handler returns a standard `(req: Request) => Promise<Response>` compatible with any Fetch API framework — Next.js App Router, Hono, SvelteKit, Cloudflare Workers, etc.

## Installation

```bash
npm install @genkit-ai/vercel-ai-sdk
```

**Peer dependencies:** `ai >= 6.0.0`, `genkit`, `zod`

## Handlers

### `chatHandler` — `useChat()`

Wraps a flow that takes `MessagesSchema` as input and emits `StreamChunkSchema` stream chunks.

```ts
// src/app/api/chat/route.ts
import { chatHandler } from '@genkit-ai/vercel-ai-sdk';
import { chatFlow } from '@/genkit/chat';

export const POST = chatHandler(chatFlow);
```

```ts
// src/genkit/chat.ts
import {
  FlowOutputSchema, MessagesSchema, StreamChunkSchema,
  toFlowOutput, toStreamChunks,
} from '@genkit-ai/vercel-ai-sdk';

export const chatFlow = ai.defineFlow(
  {
    name: 'chat',
    inputSchema: MessagesSchema,
    outputSchema: FlowOutputSchema,
    streamSchema: StreamChunkSchema,
  },
  async (input, { sendChunk }) => {
    const { stream, response } = ai.generateStream({
      messages: input.messages,
    });
    for await (const chunk of stream) {
      for (const c of toStreamChunks(chunk)) sendChunk(c);
    }
    return toFlowOutput(await response);
  }
);
```

### `completionHandler` — `useCompletion()`

Wraps a flow that takes `z.string()` as input and uses `StreamChunkSchema` as `streamSchema`. Supports both SSE (`'data'`) and plain text (`'text'`) stream protocols — in text mode only `{ type: 'text', delta }` chunks are forwarded; all other chunk types are skipped.

```ts
// src/app/api/completion/route.ts
import { completionHandler } from '@genkit-ai/vercel-ai-sdk';
import { completionFlow } from '@/genkit/completion';

export const POST = completionHandler(completionFlow);
// Or for streamProtocol: 'text':
// export const POST = completionHandler(completionFlow, { streamProtocol: 'text' });
```

### `objectHandler` — `useObject()`

Wraps a flow that streams raw JSON text fragments. `useObject` reassembles them into a typed partial object in real time.

```ts
// src/app/api/notifications/route.ts
import { objectHandler } from '@genkit-ai/vercel-ai-sdk';
import { notificationsFlow } from '@/genkit/notifications';

export const POST = objectHandler(notificationsFlow);
```

## StreamChunkSchema

A discriminated union flows can use as `streamSchema` to drive the full UI Message Stream protocol:

| Chunk type | Wire events emitted |
|---|---|
| `{ type: 'text', delta }` | `text-start` (lazy) + `text-delta` |
| `{ type: 'reasoning', delta }` | `reasoning-start` (lazy) + `reasoning-delta` |
| `{ type: 'tool-request', toolCallId, toolName, inputDelta? \| input? }` | `tool-input-start` + `tool-input-delta` or `tool-input-available` |
| `{ type: 'tool-result', toolCallId, output }` | `tool-output-available` |
| `{ type: 'tool-input-error', toolCallId, toolName, input, errorText }` | `tool-input-start` + `tool-input-error` |
| `{ type: 'tool-output-error', toolCallId, errorText }` | `tool-output-error` |
| `{ type: 'tool-output-denied', toolCallId }` | `tool-output-denied` |
| `{ type: 'tool-approval-request', approvalId, toolCallId }` | `tool-approval-request` |
| `{ type: 'file', url, mediaType }` | `file` |
| `{ type: 'source-url', sourceId, url, title? }` | `source-url` |
| `{ type: 'source-document', sourceId, mediaType, title, filename? }` | `source-document` |
| `{ type: 'data', id, value }` | `data-${id}` |
| `{ type: 'step-start' }` | `start-step` |
| `{ type: 'step-end' }` | `finish-step` + closes open blocks |

In `completionHandler` with `streamProtocol: 'text'`, only `{ type: 'text', delta }` chunks are forwarded; all other chunk types are skipped.

## Auth / Context

All three handlers accept a `contextProvider` to extract server-side context (e.g. from auth headers) and forward it to the flow:

```ts
export const POST = chatHandler(chatFlow, {
  contextProvider: async ({ headers }) => {
    const token = headers['authorization']?.slice(7);
    if (!token) throw Object.assign(new Error('Unauthorized'), { status: 401 });
    return { userId: await verifyToken(token) };
  },
});
```

## Client-supplied context

### `useChat` body passthrough

Extra fields sent by the client via `useChat({ body: { ... } })` are forwarded to the flow as `input.body`:

```ts
// Client
const { messages } = useChat({ api: '/api/chat', body: { sessionId: 'abc' } });

// Flow receives: { messages: [...], body: { sessionId: 'abc' } }
```

### `useCompletion` body passthrough

Extra fields sent via `useCompletion({ body: { ... } })` are available in `contextProvider`. Place anything the flow needs into the returned context object — Genkit stores it in async-local storage so `ai.generate()` calls and tools within the flow can access it automatically:

```ts
export const POST = completionHandler(completionFlow, {
  contextProvider: async ({ headers, input }) => {
    const token = headers['authorization']?.slice(7);
    return { userId: await verifyToken(token), sessionId: input.sessionId };
  },
});
```

## Framework compatibility

Handlers return a standard Fetch API `Response` and work in any runtime that supports the Web Platform APIs:

- **Next.js** App Router (Node.js and Edge)
- **Hono**, **SvelteKit**, **Remix**, **Astro**
- **Cloudflare Workers**, **Deno**, **Bun**

## License

Apache 2.0
