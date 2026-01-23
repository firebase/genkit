# RFC: Reflection API for Agents and Sessions

## Summary

Extends the Genkit Reflection API to support introspection and interaction with Agent primitives and their associated sessions. This enables the Developer UI to:
- List and inspect defined agents
- View and manage agent sessions
- Execute agent conversations from the UI
- Monitor agent state and message history
- Debug and test agent behavior interactively

This RFC complements the [Agent Primitive RFC](https://github.com/firebase/genkit/pull/4212) by providing the necessary API surface for tooling integration.

## Motivation

With the introduction of the `defineAgent` primitive, developers need tooling support to:

1. **Development & Testing**: Quickly test agent behavior with different inputs without writing test code
2. **Debugging**: Inspect conversation history, state transitions
3. **Session Management**: View active sessions, their state, and message history
4. **State Inspection**: Examine both client-managed and server-managed state
5. **Artifact Viewing**: Inspect generated artifacts (reports, images, etc.)
6. **Multi-turn Conversations**: Conduct full conversations with agents directly from the UI

Currently, the Reflection API supports actions and flows but lacks awareness of the Agent abstraction layer. This gap makes it difficult to leverage the Developer UI for agent development workflows.

## Design

### 1. New API Endpoints

#### A. List Agents

**Endpoint**: `GET /api/agents`

Lists all defined agents in the application with their metadata.

**Response**:
```json
{
  "agents": {
    "myAgent": {
      "name": "myAgent",
      "description": "A helpful customer service agent",
      "hasStore": false,
      "metadata": {
        "version": "1.0.0",
        "tags": ["customer-service", "support"]
      }
    },
    "persistentAgent": {
      "name": "persistentAgent", 
      "description": "An agent with server-side state",
      "hasStore": true,
      "storeType": "postgres",
      "metadata": {}
    }
  }
}
```

#### B. Get Agent Details

**Endpoint**: `GET /api/agents/{agentName}`

Retrieves detailed information about a specific agent including its schemas.

**Response**:
```json
{
  "name": "myAgent",
  "description": "A helpful customer service agent",
  "hasStore": false,
  "initSchema": {
    "type": "object",
    "properties": {
      "sessionId": {"type": "string"},
      "messages": {"type": "array"},
      "state": {},
      "artifacts": {"type": "array"}
    }
  },
  "inputSchema": {
    "type": "object",
    "properties": {
      "content": {"type": "string"}
    }
  },
  "outputSchema": {
    "type": "object", 
    "properties": {
      "sessionId": {"type": "string"},
      "messages": {"type": "array"},
      "state": {},
      "artifacts": {"type": "array"}
    }
  },
  "streamSchema": {
    "type": "object",
    "properties": {
      "sessionId": {"type": "string"},
      "chunk": {},
      "stateUpdate": {},
      "artifact": {}
    }
  },
  "metadata": {}
}
```

#### C. List Sessions

**Endpoint**: `GET /api/agents/{agentName}/sessions`

Lists all sessions for a given agent. Only available for agents with server-side stores.

**Query Parameters**:
- `limit` (optional): Maximum number of sessions to return (default: 50)
- `continuationToken` (optional): Token for pagination
- `status` (optional): Filter by session status (active, completed)

**Response**:
```json
{
  "sessions": [
    {
      "sessionId": "sess_abc123",
      "agentName": "persistentAgent",
      "createdAt": 1705968000000,
      "updatedAt": 1705968300000,
      "status": "active",
      "messageCount": 5,
      "hasArtifacts": true,
      "metadata": {
        "userId": "user_xyz"
      }
    }
  ],
  "continuationToken": "next_page_token"
}
```

#### D. Get Session Details

**Endpoint**: `GET /api/agents/{agentName}/sessions/{sessionId}`

Retrieves complete session data including messages, state, and artifacts.

**Response**:
```json
{
  "sessionId": "sess_abc123",
  "agentName": "persistentAgent",
  "createdAt": 1705968000000,
  "updatedAt": 1705968300000,
  "status": "active",
  "state": {
    "currentTopic": "greeting",
    "userPreferences": {},
    "artifacts": [
      {
        "name": "summary",
        "parts": [{"text": "Conversation summary..."}],
        "metadata": {"generatedAt": 1705968200000}
      }
    ]
  },
  "threads": {
    "main": [
      {
        "role": "user",
        "content": [{"text": "Hello!"}]
      },
      {
        "role": "model",
        "content": [{"text": "Hi! How can I help you?"}]
      }
    ]
  },
  "metadata": {}
}
```

**Note**: Messages are stored in `threads` (typically `"main"` for the primary conversation). The `state` field contains custom session state including agent-specific data like artifacts.

#### E. Start Agent Conversation

**Endpoint**: `POST /api/agents/{agentName}/execute`

Starts or continues a conversation with an agent. Supports both streaming and non-streaming execution.

**Request Body**:
```json
{
  "input": {
    "role": "user",
    "content": [{"text": "What's the weather like?"}]
  },
  "init": {
    "sessionId": "sess_abc123",
    "messages": [...],
    "state": {},
    "artifacts": []
  },
  "stream": true,
  "telemetryLabels": {
    "source": "dev-ui",
    "userId": "dev_user"
  }
}
```

**Response (Non-streaming)**:
```json
{
  "result": {
    "sessionId": "sess_abc123",
    "messages": [...],
    "state": {},
    "artifacts": []
  },
  "telemetry": {
    "traceId": "trace_xyz",
    "spanId": "span_abc"
  }
}
```

**Response (Streaming)**:
Server-sent events stream with the following event types:

```
event: chunk
data: {"sessionId": "sess_abc123", "chunk": {"content": [{"text": "The"}]}}

event: chunk  
data: {"sessionId": "sess_abc123", "chunk": {"content": [{"text": " weather"}]}}

event: stateUpdate
data: {"sessionId": "sess_abc123", "stateUpdate": {"status": "fetching_weather"}}

event: artifact
data: {"sessionId": "sess_abc123", "artifact": {"name": "map", "parts": [...]}}

event: done
data: {"sessionId": "sess_abc123", "messages": [...], "state": {...}}

event: telemetry
data: {"traceId": "trace_xyz"}
```

#### F. Delete Session

**Endpoint**: `DELETE /api/agents/{agentName}/sessions/{sessionId}`

Deletes a session and its associated state. Only available for agents with server-side stores.

**Response**:
```json
{
  "success": true,
  "sessionId": "sess_abc123"
}
```

### 3. Implementation Considerations

#### A. Agent Registry

The Genkit runtime needs to maintain a registry of defined agents, similar to how actions are registered. This registry should:

- Store agent metadata (name, description, schemas, store configuration)
- Provide lookup by agent name
- Expose agents to the Reflection API server

#### B. Store Abstraction

For agents with server-side stores, Genkit already provides a `SessionStore` interface:

```typescript
// From js/ai/src/session.ts
export interface SessionStore<S = any> {
  get(sessionId: string): Promise<SessionData<S> | undefined>;
  save(sessionId: string, data: Omit<SessionData<S>, 'id'>): Promise<void>;
}

export interface SessionData<S = any> {
  id: string;
  state?: S;
  threads?: Record<string, MessageData[]>;
}
```

**Reflection API Integration**:

- The Reflection API should leverage the existing `SessionStore` interface
- For listing sessions, the Reflection API may need to extend the interface with:
  - `list(options)`: List sessions with pagination (optional extension)
  - `delete(sessionId)`: Remove session and state (optional extension)
- Stores can implement these additional methods if they support bulk operations
- The API will work with the core `get`/`save` methods for individual session operations
