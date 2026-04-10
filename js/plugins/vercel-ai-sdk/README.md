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
import { FlowOutputSchema, MessagesSchema, StreamChunkSchema } from '@genkit-ai/vercel-ai-sdk';
import type { MessageData } from 'genkit';

export const chatFlow = ai.defineFlow(
  {
    name: 'chat',
    inputSchema: MessagesSchema,
    outputSchema: FlowOutputSchema,
    streamSchema: StreamChunkSchema,
  },
  async (input, { sendChunk }) => {
    const { stream, response } = ai.generateStream({
      messages: input.messages as MessageData[],
    });
    for await (const chunk of stream) {
      if (chunk.text) sendChunk({ type: 'text', delta: chunk.text });
    }
    const res = await response;
    return { finishReason: res.finishReason, usage: res.usage };
  }
);
```

### `completionHandler` — `useCompletion()`

Wraps a flow that takes `z.string()` as input. Supports both SSE (`'data'`) and plain text (`'text'`) stream protocols.

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
| `{ type: 'file', url, mediaType }` | `file` |
| `{ type: 'source-url', sourceId, url, title? }` | `source-url` |
| `{ type: 'source-document', sourceId, mediaType, title, filename? }` | `source-document` |
| `{ type: 'data', id, value }` | `data-${id}` |
| `{ type: 'step-start' }` | `start-step` |
| `{ type: 'step-end' }` | `finish-step` + closes open blocks |

Plain `string` chunks are also accepted for backward compatibility (treated as `{ type: 'text', delta }`).

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

## Client-supplied context (`useChat` body passthrough)

Extra fields sent by the client via `useChat({ body: { ... } })` are forwarded to the flow as `input.body`:

```ts
// Client
const { messages } = useChat({ api: '/api/chat', body: { sessionId: 'abc' } });

// Flow receives: { messages: [...], body: { sessionId: 'abc' } }
```

## Framework compatibility

Handlers return a standard Fetch API `Response` and work in any runtime that supports the Web Platform APIs:

- **Next.js** App Router (Node.js and Edge)
- **Hono**, **SvelteKit**, **Remix**, **Astro**
- **Cloudflare Workers**, **Deno**, **Bun**

## License

Apache 2.0
