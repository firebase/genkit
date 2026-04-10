# vercel-ai-sdk-next

Sample Next.js app demonstrating the `@genkit-ai/vercel-ai-sdk` plugin. Shows how to wire Genkit flows to the Vercel AI SDK UI hooks using the three adapter handlers.

## What's demonstrated

| Page | Hook | Handler | Flow |
|------|------|---------|------|
| `/chat` | `useChat` | `chatHandler` | Multi-turn chat with streaming text via `MessagesSchema` + `StreamChunkSchema` |
| `/completion` | `useCompletion` | `completionHandler` | Single-turn text completion with SSE streaming |
| `/object` | `useObject` | `objectHandler` | Structured JSON streaming — generates typed notification objects in real time |

## Prerequisites

- **Node.js** v18+
- **pnpm**
- A **Gemini API key** — get one at [aistudio.google.com](https://aistudio.google.com)

## Setup

From the repo root, install all workspace dependencies:

```bash
pnpm install
```

Set your API key:

```bash
export GEMINI_API_KEY=your_api_key_here
```

## Run

```bash
cd js/testapps/vercel-ai-sdk-next
pnpm dev
```

The app starts at [http://localhost:3000](http://localhost:3000).

## Project structure

```
src/
  app/
    api/
      chat/route.ts        # POST handler using chatHandler()
      completion/route.ts  # POST handler using completionHandler()
      object/route.ts      # POST handler using objectHandler()
    chat/page.tsx          # useChat demo UI
    completion/page.tsx    # useCompletion demo UI
    object/page.tsx        # useObject demo UI
  genkit/
    index.ts               # Genkit + googleAI plugin initialization
    chat.ts                # chatFlow: MessagesSchema + StreamChunkSchema
    completion.ts          # completionFlow: z.string() stream
    object.ts              # notificationsFlow: structured JSON streaming
  schemas.ts               # Shared Zod schemas (NotificationsSchema)
```

## How it works

Each API route is a one-liner that wraps a Genkit flow:

```ts
// src/app/api/chat/route.ts
import { chatHandler } from '@genkit-ai/vercel-ai-sdk';
import { chatFlow } from '@/genkit/chat';

export const POST = chatHandler(chatFlow);
```

The flow defines its input and stream schemas using types from the plugin:

```ts
// src/genkit/chat.ts
export const chatFlow = ai.defineFlow(
  {
    inputSchema: MessagesSchema,   // receives UIMessage[] converted to Genkit format
    streamSchema: StreamChunkSchema, // drives the full useChat protocol
    outputSchema: FlowOutputSchema,  // surfaces finishReason + usage
  },
  async (input, { sendChunk }) => { ... }
);
```

## License

Apache 2.0
