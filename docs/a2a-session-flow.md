# A2A Adapter for Genkit Session Flows

This document outlines the design for the `@genkit-ai/a2a` plugin package, which provides an adapter between Genkit Session Flows and the Agent-to-Agent (A2A) protocol using the `@a2a-js/sdk`.

## Overview: A2A vs Genkit Session Flow

### What is A2A?
The Agent-to-Agent (A2A) protocol is a communication standard for autonomous agents. It defines how agents discover each other (via Agent Cards), send messages, manage long-running stateful operations (Tasks), and receive updates via streaming or push notifications. It is transport-agnostic, supporting JSON-RPC, REST, and gRPC.

### What is Genkit Session Flow?
Genkit Session Flows provide a framework for building multi-turn, interactive AI applications. They maintain state across executions (via snapshots), support streaming responses, and allow for complex behaviors like branching history and client-managed state.

### Overlap
Both systems share core concepts:
- **Multi-turn interaction**: Both support ongoing conversations with history.
- **Streaming**: Both support real-time chunk delivery.
- **Statefulness**: A2A `Tasks` map conceptually to Genkit `Sessions`.
- **Artifacts**: Both allow agents to produce and share files or structured data.
- **Cancellation**: Both support aborting ongoing operations.

### Differences and Non-Overlap
- **Protocol vs. Framework**: A2A is a protocol specification with a light SDK; Genkit is a full-featured application framework.
- **Push Notifications**: A2A supports webhook-based push notifications for long-running tasks. Genkit Session Flows rely on active connections (SSE/WebSockets) and do not have built-in push notification mechanisms.
- **State Management**: Genkit allows for extreme flexibility, including branching history and client-echoed state. A2A typically assumes a linear task history stored on the server.

### Features Hard to Adapt or Omitted
- **Full Push Notification Support**: Without a Genkit-native way to register and trigger webhooks for clients, full A2A push notification support will require custom implementation in the adapter (e.g., an Express webhook sender) or be left as an extension point.
- **Genkit Branching to A2A**: Standard A2A clients expect a linear sequence of events for a task. Exposing Genkit's ability to branch history from an older snapshot might require generating new A2A `contextId`s or `taskId`s to prevent history corruption in the client.

---

The adapter serves two main purposes:
1. **Expose** a Genkit `SessionFlow` as an A2A-compliant agent.
2. **Consume** an existing A2A agent as a Genkit `SessionFlow`.

---

## 1. Exposing Genkit Session Flow as an A2A Agent

To expose a Genkit `SessionFlow` as an A2A agent, we implement the `AgentExecutor` interface from the A2A SDK. This allows the session flow to be served via JSON-RPC, REST, or gRPC using the A2A server infrastructure.

### Architecture

- **`SessionFlowAgentExecutor`**: Implements `AgentExecutor`. It wraps a Genkit `SessionFlow` and translates A2A `RequestContext` and incoming messages into Genkit inputs.
- **Session Management**: The Genkit `SessionFlow` typically uses a `SessionStore`. We can map the A2A `contextId` to the Genkit `snapshotId` to maintain session continuity across turns.
- **Streaming**: Genkit stream chunks are mapped to A2A events (messages, status updates, artifacts) and published to the A2A `ExecutionEventBus`.

### Code Sample: Implementation

```typescript
import { AgentExecutor, RequestContext, ExecutionEventBus } from '@a2a-js/sdk/server';
import { SessionFlow, SessionFlowInput } from '@genkit-ai/ai'; // Conceptual import
import { v4 as uuidv4 } from 'uuid';

export class SessionFlowAgentExecutor implements AgentExecutor {
  constructor(private sessionFlow: SessionFlow) {}

  async execute(requestContext: RequestContext, eventBus: ExecutionEventBus): Promise<void> {
    const { taskId, contextId, userMessage, task } = requestContext;

    // 1. Map A2A Message to Genkit Input
    const genkitInput: SessionFlowInput = {
      messages: [{
        role: 'user',
        content: userMessage.parts.map(p => {
          if (p.kind === 'text') return { text: p.text };
          return { text: JSON.stringify(p) }; // Fallback
        })
      }]
    };

    // 2. Run the Session Flow and handle the stream
    // Note: We assume a way to run the BidiAction with an input stream or direct call
    const stream = this.sessionFlow.runStream(genkitInput, {
      init: { snapshotId: contextId } // Map A2A contextId to Genkit snapshotId
    });

    try {
      for await (const chunk of stream) {
        // Handle Model Chunks (Messages)
        if (chunk.modelChunk?.content) {
          eventBus.publish({
            kind: 'message',
            messageId: uuidv4(),
            role: 'agent',
            parts: chunk.modelChunk.content.map(p => {
              if (p.text) return { kind: 'text', text: p.text };
              return { kind: 'text', text: JSON.stringify(p) }; // Fallback
            }),
            contextId,
          });
        }

        // Handle Custom Status Updates
        if (chunk.status) {
          eventBus.publish({
            kind: 'status-update',
            taskId,
            contextId,
            status: { state: chunk.status, timestamp: new Date().toISOString() },
            final: false,
          });
        }

        // Handle Artifacts
        if (chunk.artifact) {
          eventBus.publish({
            kind: 'artifact-update',
            taskId,
            contextId,
            artifact: chunk.artifact, // Assuming shape compatibility or mapping
          });
        }
      }
    } catch (error: any) {
      eventBus.publish({
        kind: 'status-update',
        taskId,
        contextId,
        status: { state: 'failed', timestamp: new Date().toISOString() },
        final: true,
        error: { status: 'INTERNAL', message: error.message }
      });
      throw error;
    }

    // Signal completion
    eventBus.finished();
  }

  async cancelTask(taskId: string, eventBus: ExecutionEventBus): Promise<void> {
    // Handle cancellation by aborting the Genkit session if supported
    // sessionFlow.abort(taskId);
  }
}
```

### Code Sample: Serving the Agent

```typescript
import express from 'express';
import { AgentCard } from '@a2a-js/sdk';
import { DefaultRequestHandler, InMemoryTaskStore } from '@a2a-js/sdk/server';
import { jsonRpcHandler, restHandler } from '@a2a-js/sdk/server/express';
import { SessionFlowAgentExecutor } from '@genkit-ai/a2a';
import { mySessionFlow } from './my-flow'; // Your Genkit flow

const card: AgentCard = {
  name: 'Genkit Agent',
  description: 'Genkit Session Flow exposed via A2A',
  protocolVersion: '0.3.0',
  version: '0.1.0',
  url: 'http://localhost:4000/a2a/jsonrpc',
  skills: [{ id: 'genkit-flow', name: 'Genkit Flow', description: 'Runs Genkit logic' }],
  defaultInputModes: ['text'],
  defaultOutputModes: ['text'],
};

const executor = new SessionFlowAgentExecutor(mySessionFlow);
const requestHandler = new DefaultRequestHandler(card, new InMemoryTaskStore(), executor);

const app = express();
app.use('/a2a/jsonrpc', jsonRpcHandler({ requestHandler }));
app.use('/a2a/rest', restHandler({ requestHandler }));

app.listen(4000, () => console.log('A2A Agent listening on port 4000'));
```

---

## 2. Consuming A2A Agent as Genkit Session Flow

To consume an A2A agent, we create a Genkit `SessionFlow` that acts as a client to the A2A agent. This allows Genkit users to interact with A2A agents as if they were native session flows.

### Architecture

- **`defineA2ASessionFlow`**: A helper function that registers a `SessionFlow`.
- **Client Factory**: Uses A2A `ClientFactory` to create a client connected to the remote agent.
- **Turn Management**: Inside `sess.run`, incoming Genkit messages are forwarded to the A2A agent via `sendMessageStream` or `sendMessage`.
- **Stream Mapping**: A2A events are mapped back to Genkit `SessionFlowStreamChunk`s.

### Code Sample: Usage

```typescript
import { ai } from './genkit.js';
import { defineA2ASessionFlow } from '@genkit-ai/a2a';
import { z } from 'genkit';

// Define a Genkit Session Flow that wraps a remote A2A agent
export const remoteA2AAgent = defineA2ASessionFlow(ai, {
  name: 'remoteA2AAgent',
  description: 'Consumes a remote A2A agent',
  agentUrl: 'http://localhost:4000/a2a/jsonrpc', // URL of the A2A agent
});

// Test the flow
export const testFlow = ai.defineFlow(
  {
    name: 'testFlow',
    inputSchema: z.string(),
    outputSchema: z.any(),
  },
  async (text) => {
    const res = await remoteA2AAgent.run(
      {
        messages: [{ role: 'user', content: [{ text }] }],
      },
      { init: {} }
    );
    return res.result;
  }
);
```

---

## 3. Feature Coverage & Advanced Concepts

### Tasks and Persistence
- **A2A Tasks**: Mapped to Genkit Session turns or long-running background operations if `detach` is used.
- **Persistence**: Genkit `SessionStore` can be used on the server side to persist session state, which aligns with A2A's expectation of stateful interactions for tasks.

### Cancellation
- A2A `cancelTask` triggers an abort.
- The adapter should map this to Genkit's `sessionFlow.abort(snapshotId)` if a persistent store is used, which sets the status to 'aborted' and triggers the `AbortController`.

### Branching
- Genkit supports branching history by resuming from older `snapshotId`s.
- In A2A, this maps to creating a new interaction context or task derived from a previous state. The adapter should support using the A2A `contextId` to lookup and resume specific Genkit snapshots, enabling branching if the client initiates a new task from an older context.

### Client-Side (Stateless) State
- In Genkit, agents can be run without a store, returning the full `state` to the client to be echoed back.
- **Exposing**: When exposing a stateless Genkit flow as A2A, the adapter must manage this state. Since A2A expects server-side storage (e.g., `TaskStore`), the adapter should store the echoed Genkit state in the A2A `TaskStore` indexed by `taskId` or `contextId`.
- **Consuming**: When consuming a stateful A2A agent as Genkit, the adapter relies on the remote A2A server's task state and doesn't need to pass state back to the client.

### Push Notifications
- The adapter can support A2A push notifications by providing a webhook endpoint that maps incoming POST requests from the A2A server back into the Genkit session or flow execution context.
