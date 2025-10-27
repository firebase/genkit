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

# Anthropic Plugin Test Mocks

Mock utilities for testing the Anthropic plugin without making real API calls.

## Quick Start

```typescript
import { setupAnthropicMock } from './mocks/setup-anthropic-mock.js';

// Set up SDK mocking (call at module level, before describe blocks)
setupAnthropicMock();

describe('My Test Suite', () => {
  // Your tests here
});
```

## setupAnthropicMock()

Sets up mocking for the Anthropic SDK module. Must be called at the module level before any describe blocks.

### Basic Usage

```typescript
setupAnthropicMock();
```

### Custom Response

```typescript
setupAnthropicMock({
  messageResponse: {
    content: [{ type: 'text', text: 'Custom response' }]
  }
});
```

### Return Value

Returns `{ mockClient, mockResponse }` for making assertions in tests.

```typescript
const { mockClient } = setupAnthropicMock();

// Later in tests, verify SDK was called
assert.ok(mockClient.messages.create.mock.calls.length > 0);
```

## createMockAnthropicMessage()

Creates customizable mock Anthropic Message responses for more complex test scenarios.

### Text Response

```typescript
import { createMockAnthropicMessage } from './mocks/anthropic-client.js';

const message = createMockAnthropicMessage({
  text: 'Hello from test'
});
```

### Tool Use Response

```typescript
const message = createMockAnthropicMessage({
  toolUse: {
    name: 'get_weather',
    input: { city: 'NYC' }
  }
});
```

### Custom Tokens

```typescript
const message = createMockAnthropicMessage({
  usage: {
    input_tokens: 100,
    output_tokens: 500
  }
});
```

### All Options

```typescript
const message = createMockAnthropicMessage({
  id: 'msg_custom',           // Default: 'msg_test123'
  text: 'Custom text',        // Default: 'Hello! How can I help you today?'
  toolUse: {                  // Mutually exclusive with text
    id: 'tool_123',           // Default: 'toolu_test123'
    name: 'tool_name',        // Required
    input: {}                 // Required
  },
  stopReason: 'end_turn',    // Default: 'end_turn' or 'tool_use'
  usage: {
    input_tokens: 10,
    output_tokens: 20,
    cache_creation_input_tokens: 0,
    cache_read_input_tokens: 0
  }
});
```

## Other Helpers

### createMockAnthropicClient()

Creates a mock Anthropic client with configurable responses for more complex test scenarios.

```typescript
import { createMockAnthropicClient } from './mocks/anthropic-client.js';

const mockClient = createMockAnthropicClient({
  messageResponse: { content: [{ type: 'text', text: 'Response' }] },
  streamChunks: [mockTextChunk('chunk1'), mockTextChunk('chunk2')],
  shouldError: new Error('API Error')
});
```

### Stream Event Helpers

```typescript
import {
  mockTextChunk,
  mockContentBlockStart,
  mockToolUseChunk
} from './mocks/anthropic-client.js';

// Text delta for streaming
const chunk = mockTextChunk('Hello');

// Content block start
const start = mockContentBlockStart('Starting text');

// Tool use event
const toolChunk = mockToolUseChunk('tool_id', 'tool_name', { arg: 'value' });
```

## Pattern: Testing Plugin Lifecycle

```typescript
import { setupAnthropicMock } from './mocks/setup-anthropic-mock.js';

setupAnthropicMock();

describe('Plugin Tests', () => {
  let anthropic: any;

  before(async () => {
    const { anthropic: plugin } = await import('../src/index.js');
    anthropic = plugin;
  });

  it('should initialize correctly', () => {
    // Test plugin initialization
  });
});
```

## Pattern: Testing Integration

```typescript
import { genkit } from 'genkit';
import { setupAnthropicMock } from './mocks/setup-anthropic-mock.js';

setupAnthropicMock({
  messageResponse: {
    content: [{ type: 'text', text: 'Test response' }]
  }
});

describe('Integration Tests', () => {
  let ai: Genkit;

  before(async () => {
    const { anthropic } = await import('../src/index.js');
    ai = genkit({ plugins: [anthropic()] });
  });

  it('should generate responses', async () => {
    const result = await ai.generate({
      model: 'anthropic/claude-3-5-sonnet',
      prompt: 'Test'
    });

    assert.strictEqual(result.text, 'Test response');
  });
});
```
