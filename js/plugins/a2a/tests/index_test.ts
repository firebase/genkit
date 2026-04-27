import { test } from 'node:test';
import * as assert from 'node:assert';
import { SessionFlowAgentExecutor, defineA2ASessionFlow, mapGenkitPartToA2A, mapA2APartToGenkit, mapGenkitArtifactToA2A, mapA2AArtifactToGenkit } from '../src/index.js';
import { genkit } from 'genkit/beta';
import { RequestContext, ExecutionEventBus } from '@a2a-js/sdk/server';
import type { Message as A2AMessage, TaskStatusUpdateEvent as A2ATaskStatusUpdateEvent, DataPart as A2ADataPart, MessageSendParams as A2AMessageSendParams, Part as A2APart } from '@a2a-js/sdk';

test('SessionFlowAgentExecutor can be instantiated', () => {
  const ai = genkit({});
  
  const dummyFlow = ai.defineSessionFlow(
    { name: 'dummyFlow' },
    async (sess) => {
      await sess.run(async () => {});
      return { message: { role: 'model', content: [] } };
    }
  );

  const executor = new SessionFlowAgentExecutor(dummyFlow);
  assert.ok(executor);
});

test('defineA2ASessionFlow returns a flow', () => {
  const ai = genkit({});
  
  const flow = defineA2ASessionFlow(ai, {
    name: 'remoteAgent',
    agentUrl: 'http://localhost:4000',
  });

  assert.ok(flow);
});

// Extensive Mapping Tests

test('mapGenkitPartToA2A maps text parts', () => {
  const part = { text: 'hello' };
  const mapped = mapGenkitPartToA2A(part);
  assert.deepStrictEqual(mapped, { kind: 'text', text: 'hello' });
});

test('mapGenkitPartToA2A maps remote file parts', () => {
  const part = { media: { url: 'http://example.com/image.png', contentType: 'image/png' } };
  const mapped = mapGenkitPartToA2A(part);
  assert.deepStrictEqual(mapped, {
    kind: 'file',
    file: {
      uri: 'http://example.com/image.png',
      mimeType: 'image/png',
      name: 'remote_file',
    },
  });
});

test('mapGenkitPartToA2A maps inline file parts', () => {
  const part = { media: { url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', contentType: 'image/png' } };
  const mapped = mapGenkitPartToA2A(part);
  assert.deepStrictEqual(mapped, {
    kind: 'file',
    file: {
      bytes: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
      mimeType: 'image/png',
      name: 'inline_file',
    },
  });
});

test('mapGenkitPartToA2A uses DataPart for complex parts', () => {
  const part = { custom: { foo: 'bar' } };
  const mapped = mapGenkitPartToA2A(part);
  assert.strictEqual(mapped.kind, 'data');
  assert.deepStrictEqual((mapped as A2ADataPart).data, part);
});

test('mapA2APartToGenkit maps text parts', () => {
  const part = { kind: 'text', text: 'hello' } as const;
  const mapped = mapA2APartToGenkit(part);
  assert.deepStrictEqual(mapped, { text: 'hello' });
});

test('mapA2APartToGenkit maps file parts with URI', () => {
  const part = {
    kind: 'file',
    file: {
      uri: 'http://example.com/image.png',
      mimeType: 'image/png',
      name: 'remote_file',
    },
  } as const;
  const mapped = mapA2APartToGenkit(part);
  assert.deepStrictEqual(mapped, {
    media: {
      url: 'http://example.com/image.png',
      contentType: 'image/png',
    },
  });
});

test('mapA2APartToGenkit maps file parts with bytes', () => {
  const part = {
    kind: 'file',
    file: {
      bytes: 'base64data',
      mimeType: 'image/png',
      name: 'inline_file',
    },
  } as const;
  const mapped = mapA2APartToGenkit(part);
  assert.deepStrictEqual(mapped, {
    media: {
      url: 'data:image/png;base64,base64data',
      contentType: 'image/png',
    },
  });
});

test('mapA2APartToGenkit does not restore JSON objects with unknown keys', () => {
  // 'toolCall' is not a valid Genkit Part key — unknown objects stay as text
  const unknownObj = { toolCall: { name: 'myTool', args: {} } };
  const part = { kind: 'text', text: JSON.stringify(unknownObj) } as const;
  const mapped = mapA2APartToGenkit(part);
  assert.deepStrictEqual(mapped, { text: JSON.stringify(unknownObj) });
});

test('mapA2APartToGenkit maps DataPart to Genkit data part for unknown keys', () => {
  const unknownObj = { toolCall: { name: 'myTool', args: {} } };
  const part = { kind: 'data', data: unknownObj } as const;
  const mapped = mapA2APartToGenkit(part as unknown as A2APart);
  assert.deepStrictEqual(mapped, { data: unknownObj });
});

// Execution Flow Tests

test('SessionFlowAgentExecutor execute publishes messages', async () => {
  const ai = genkit({});
  const realFlow = ai.defineSessionFlow(
    { name: 'realFlow' },
    async (sess, { sendChunk }) => {
      await sess.run(async () => {
        sendChunk({ modelChunk: { content: [{ text: 'response' }] } });
      });
      return { message: { role: 'model', content: [] } };
    }
  );

  const executor = new SessionFlowAgentExecutor(realFlow);
  
  const publishedEvents: Record<string, unknown>[] = [];
  const mockEventBus = {
    publish: (event: Record<string, unknown>) => { publishedEvents.push(event); },
    finished: () => {},
  };
  
  const mockRequestContext = {
    taskId: 'task-1',
    contextId: 'context-1',
    userMessage: {
      parts: [{ kind: 'text' as const, text: 'hello' }],
    },
  };
  
  await executor.execute(mockRequestContext as unknown as RequestContext, mockEventBus as unknown as ExecutionEventBus);

  // Lifecycle: task(submitted) + working + <message> + completed
  const messageEvents = publishedEvents.filter((e) => e.kind === 'message');
  assert.equal(messageEvents.length, 1);
  const parts = messageEvents[0].parts as { kind: string, text: string }[];
  assert.equal(parts[0].text, 'response');
});

test('SessionFlowAgentExecutor emits input-required when flow returns toolRequest', async () => {
  const ai = genkit({});
  const toolFlow = ai.defineSessionFlow(
    { name: 'toolFlow' },
    async (sess, { sendChunk }) => {
      await sess.run(async () => {
        sendChunk({ modelChunk: { role: 'model', content: [{ toolRequest: { name: 'myTool', input: {}, ref: '123' } }] } });
      });
      return { 
        message: { 
          role: 'model', 
          content: [{ toolRequest: { name: 'myTool', input: {}, ref: '123' } }] 
        } 
      };
    }
  );

  const executor = new SessionFlowAgentExecutor(toolFlow);
  
  const publishedEvents: Record<string, unknown>[] = [];
  const mockEventBus = {
    publish: (event: Record<string, unknown>) => { publishedEvents.push(event); },
    finished: () => {},
  };
  
  const mockRequestContext = {
    taskId: 'task-1',
    contextId: 'context-1',
    userMessage: {
      parts: [{ kind: 'text' as const, text: 'hello' }],
    },
  };
  
  await executor.execute(mockRequestContext as unknown as RequestContext, mockEventBus as unknown as ExecutionEventBus);

  // Assert status is input-required
  const statusEvents = publishedEvents.filter((e) => e.kind === 'status-update' && (e as any).final === true) as unknown as A2ATaskStatusUpdateEvent[];
  assert.equal(statusEvents.length, 1);
  assert.equal(statusEvents[0].status.state, 'input-required');

  // Assert toolRequest was correctly streamed to the client as a DataPart
  const messageEvents = publishedEvents.filter((e) => e.kind === 'message');
  assert.equal(messageEvents.length, 1);
  const dataPart = (messageEvents[0] as unknown as A2AMessage).parts[0] as A2ADataPart;
  assert.equal(dataPart.kind, 'data');
  assert.deepStrictEqual(dataPart.data.toolRequest, { name: 'myTool', input: {}, ref: '123' });
});

test('SessionFlowAgentExecutor maps A2A user messages with toolResponses to role: tool', async () => {
  const ai = genkit({});
  const toolResponseFlow = ai.defineSessionFlow(
    { name: 'toolResponseFlow' },
    async (sess) => {
      await sess.run(async () => {
        const msgs = sess.session.getMessages();
        assert.equal(msgs[msgs.length - 1].role, 'tool');
      });
      return { message: { role: 'model', content: [] } };
    }
  );

  const executor = new SessionFlowAgentExecutor(toolResponseFlow);
  
  const publishedEvents: Record<string, unknown>[] = [];
  const mockEventBus = {
    publish: (event: Record<string, unknown>) => { publishedEvents.push(event); },
    finished: () => {},
  };
  
  const mockRequestContext = {
    taskId: 'task-1',
    contextId: 'context-1',
    userMessage: {
      parts: [{ kind: 'data' as const, data: { toolResponse: { name: 'myTool', ref: '123', output: 'done' } } }],
    },
  };
  
  await executor.execute(mockRequestContext as unknown as RequestContext, mockEventBus as unknown as ExecutionEventBus);
});

test('SessionFlowAgentExecutor execute publishes status updates', async () => {
  const ai = genkit({});
  const statusFlow = ai.defineSessionFlow(
    { name: 'statusFlow' },
    async (sess, { sendChunk }) => {
      await sess.run(async () => {
        sendChunk({ status: 'working' });
      });
      return { message: { role: 'model', content: [] } };
    }
  );

  const executor = new SessionFlowAgentExecutor(statusFlow);
  
  const publishedEvents: Record<string, unknown>[] = [];
  const mockEventBus = {
    publish: (event: Record<string, unknown>) => { publishedEvents.push(event); },
    finished: () => {},
  };
  
  const mockRequestContext = {
    taskId: 'task-1',
    contextId: 'context-1',
    userMessage: {
      parts: [{ kind: 'text' as const, text: 'hello' }],
    },
  };
  
  await executor.execute(mockRequestContext as unknown as RequestContext, mockEventBus as unknown as ExecutionEventBus);

  // Lifecycle: task(submitted) + working + <status from flow> + completed
  const statusEvents = publishedEvents.filter((e) => e.kind === 'status-update') as unknown as A2ATaskStatusUpdateEvent[];
  // working (lifecycle), working (flow), completed (lifecycle)
  assert.equal(statusEvents.length, 3);
  assert.equal(statusEvents[0].status.state, 'working');   // lifecycle working
  assert.equal(statusEvents[1].status.state, 'working');   // flow sendChunk
  assert.equal(statusEvents[2].status.state, 'completed'); // lifecycle completed
});

test('SessionFlowAgentExecutor execute publishes artifacts', async () => {
  const ai = genkit({});
  const artifactFlow = ai.defineSessionFlow(
    { name: 'artifactFlow' },
    async (sess, { sendChunk }) => {
      await sess.run(async () => {
        sendChunk({ artifact: { name: 'myArtifact', parts: [{ text: 'data' }] } });
      });
      return { message: { role: 'model', content: [] } };
    }
  );

  const executor = new SessionFlowAgentExecutor(artifactFlow);
  
  const publishedEvents: Record<string, unknown>[] = [];
  const mockEventBus = {
    publish: (event: Record<string, unknown>) => { publishedEvents.push(event); },
    finished: () => {},
  };
  
  const mockRequestContext = {
    taskId: 'task-1',
    contextId: 'context-1',
    userMessage: {
      parts: [{ kind: 'text' as const, text: 'hello' }],
    },
  };
  
  await executor.execute(mockRequestContext as unknown as RequestContext, mockEventBus as unknown as ExecutionEventBus);

  // Lifecycle: task(submitted) + working + <artifact-update> + completed
  const artifactEvents = publishedEvents.filter((e) => e.kind === 'artifact-update');
  assert.equal(artifactEvents.length, 1);
  const artifact = artifactEvents[0].artifact as { artifactId: string };
  assert.equal(artifact.artifactId, 'myArtifact');
});

// Artifact Mapping Tests

test('mapGenkitArtifactToA2A maps name to artifactId and name', () => {
  const artifact = { name: 'report.txt', parts: [{ text: 'content' }] };
  const mapped = mapGenkitArtifactToA2A(artifact);
  assert.equal(mapped.artifactId, 'report.txt');
  assert.equal(mapped.name, 'report.txt');
  assert.equal(mapped.parts.length, 1);
});

test('mapGenkitArtifactToA2A allows metadata.a2a.name to override A2A name', () => {
  const artifact = {
    name: 'report-id',
    parts: [{ text: 'content' }],
    metadata: { a2a: { name: 'Human Readable Report' } },
  };
  const mapped = mapGenkitArtifactToA2A(artifact);
  assert.equal(mapped.artifactId, 'report-id');
  assert.equal(mapped.name, 'Human Readable Report');
});

test('mapGenkitArtifactToA2A maps metadata.a2a.description and extensions', () => {
  const artifact = {
    name: 'report-id',
    parts: [{ text: 'content' }],
    metadata: { a2a: { description: 'A report', extensions: ['ext1'] } },
  };
  const mapped = mapGenkitArtifactToA2A(artifact);
  assert.equal(mapped.description, 'A report');
  assert.deepStrictEqual(mapped.extensions, ['ext1']);
});

test('mapGenkitArtifactToA2A passes non-a2a metadata through to A2A metadata', () => {
  const artifact = {
    name: 'report-id',
    parts: [{ text: 'content' }],
    metadata: { custom: 'value', a2a: { name: 'override' } },
  };
  const mapped = mapGenkitArtifactToA2A(artifact);
  assert.deepStrictEqual(mapped.metadata, { custom: 'value' });
});

test('mapGenkitArtifactToA2A throws if name is absent', () => {
  const artifact = { parts: [{ text: 'content' }] };
  assert.throws(() => mapGenkitArtifactToA2A(artifact), /Artifact\.name is required/);
});

test('mapA2AArtifactToGenkit maps artifactId to name', () => {
  const artifact = { artifactId: 'report-id', parts: [{ kind: 'text' as const, text: 'content' }] };
  const mapped = mapA2AArtifactToGenkit(artifact);
  assert.equal(mapped.name, 'report-id');
  assert.equal(mapped.parts.length, 1);
});

test('mapA2AArtifactToGenkit stores a2a name, description, extensions under metadata.a2a', () => {
  const artifact = {
    artifactId: 'report-id',
    name: 'Human Readable Report',
    description: 'A report',
    extensions: ['ext1'],
    parts: [{ kind: 'text' as const, text: 'content' }],
  };
  const mapped = mapA2AArtifactToGenkit(artifact);
  assert.equal(mapped.metadata?.a2a?.name, 'Human Readable Report');
  assert.equal(mapped.metadata?.a2a?.description, 'A report');
  assert.deepStrictEqual(mapped.metadata?.a2a?.extensions, ['ext1']);
});

test('mapA2AArtifactToGenkit stores a2a metadata under metadata.a2a.metadata', () => {
  const artifact = {
    artifactId: 'report-id',
    parts: [{ kind: 'text' as const, text: 'content' }],
    metadata: { custom: 'value' },
  };
  const mapped = mapA2AArtifactToGenkit(artifact);
  assert.deepStrictEqual(mapped.metadata?.a2a?.metadata, { custom: 'value' });
});

test('mapA2AArtifactToGenkit omits metadata when no a2a fields are present', () => {
  const artifact = { artifactId: 'report-id', parts: [{ kind: 'text' as const, text: 'content' }] };
  const mapped = mapA2AArtifactToGenkit(artifact);
  assert.equal(mapped.metadata, undefined);
});

test('artifact round-trip: Genkit → A2A → Genkit preserves name and parts', () => {
  const original = {
    name: 'output.txt',
    parts: [{ text: 'hello' }],
    metadata: { a2a: { description: 'output file' } },
  };
  const a2a = mapGenkitArtifactToA2A(original);
  const restored = mapA2AArtifactToGenkit(a2a);
  assert.equal(restored.name, original.name);
  assert.equal((restored.parts[0] as { text: string }).text, 'hello');
  assert.equal(restored.metadata?.a2a?.description, 'output file');
});

test('defineA2ASessionFlow handles incoming toolRequest interrupts from remote agent', async () => {
  const ai = genkit({});
  
  const mockClient = {
    sendMessageStream: (_params: A2AMessageSendParams) => {
      return (async function* () {
        yield {
          kind: 'message' as const,
          messageId: '1',
          role: 'agent' as const,
          parts: [{ kind: 'data' as const, data: { toolRequest: { name: 'myTool', input: { query: 'test' }, ref: '123' } } }],
        } as A2AMessage;
        yield {
          kind: 'status-update' as const,
          taskId: 't1',
          contextId: 'c1',
          status: { state: 'input-required' as const },
          final: false,
        } as A2ATaskStatusUpdateEvent;
      })();
    }
  };

  const flow = defineA2ASessionFlow(ai, {
    name: 'testIncomingInterrupt',
    agentUrl: 'http://localhost:4000',
    clientFactory: { createFromUrl: async () => mockClient }
  });

  const chunks: Record<string, unknown>[] = [];
  const result = await flow.run(
    { messages: [{ role: 'user', content: [{ text: 'hello' }] }] },
    { init: {}, onChunk: (chunk) => chunks.push(chunk as Record<string, unknown>) }
  );
  
  const modelChunk = chunks.find((c) => !!c.modelChunk) as any;
  assert.ok(modelChunk);
  assert.deepStrictEqual(modelChunk.modelChunk.content[0].toolRequest, { name: 'myTool', input: { query: 'test' }, ref: '123' });
  
  const statusChunk = chunks.find((c) => !!c.status) as any;
  assert.ok(statusChunk);
  assert.equal(statusChunk.status, 'input-required');

  // Verify that the final message in the session state includes the tool request
  assert.ok(result.result.message);
  assert.deepStrictEqual((result.result.message.content[0] as any).toolRequest, { name: 'myTool', input: { query: 'test' }, ref: '123' });
});

test('defineA2ASessionFlow forwards toolRestarts to remote agent', async () => {
  const ai = genkit({});
  
  let sentParams: A2AMessageSendParams | undefined;
  const mockClient = {
    sendMessageStream: (params: A2AMessageSendParams) => {
      sentParams = params;
      return (async function* () {
        yield {
          kind: 'status-update' as const,
          taskId: 't1',
          contextId: 'c1',
          status: { state: 'working' as const },
          final: false,
        } as A2ATaskStatusUpdateEvent;
      })();
    }
  };

  const flow = defineA2ASessionFlow(ai, {
    name: 'testToolRestartAgent',
    agentUrl: 'http://localhost:4000',
    clientFactory: { createFromUrl: async () => mockClient }
  });

  await flow.run(
    { toolRestarts: [{ toolResponse: { name: 'myTool', ref: '123', output: { success: true } } }] },
    { init: {}, onChunk: () => {} }
  );
  
  assert.ok(sentParams);
  assert.equal(sentParams!.message.parts[0].kind, 'data');
  assert.deepStrictEqual(((sentParams!.message.parts[0] as A2ADataPart).data as { toolResponse: unknown }).toolResponse, { name: 'myTool', ref: '123', output: { success: true } });
});

test('defineA2ASessionFlow executes and maps incoming stream', async () => {
  const ai = genkit({});
  
  const mockClient = {
    sendMessageStream: (_params: A2AMessageSendParams) => {
      return (async function* () {
        yield {
          kind: 'message' as const,
          messageId: '1',
          role: 'agent' as const,
          parts: [{ kind: 'text' as const, text: 'a2a response' }],
        } as A2AMessage;
        yield {
          kind: 'status-update' as const,
          taskId: 't1',
          contextId: 'c1',
          status: { state: 'working' as const },
          final: false,
        } as A2ATaskStatusUpdateEvent;
      })();
    }
  };

  const mockFactory = {
    createFromUrl: async (_url: string) => mockClient
  };
  
  const flow = defineA2ASessionFlow(ai, {
    name: 'testRemoteAgent',
    agentUrl: 'http://localhost:4000',
    clientFactory: mockFactory
  });

  const chunks: Record<string, unknown>[] = [];
  await flow.run(
    { messages: [{ role: 'user', content: [{ text: 'hello' }] }] },
    { 
      init: {},
      onChunk: (chunk) => chunks.push(chunk as Record<string, unknown>)
    }
  );
  
  assert.equal(chunks.length, 3);
  const firstChunk = chunks[0] as { modelChunk: { content: { text: string }[] } };
  assert.equal(firstChunk.modelChunk.content[0].text, 'a2a response');
  const secondChunk = chunks[1] as { status: string };
  assert.equal(secondChunk.status, 'working');
  const thirdChunk = chunks[2] as { turnEnd: { snapshotId: string } };
  assert.ok(thirdChunk.turnEnd);
});

// Part mapping edge cases

test('mapGenkitPartToA2A maps empty string text part (not dropped)', () => {
  const part = { text: '' };
  const mapped = mapGenkitPartToA2A(part);
  assert.deepStrictEqual(mapped, { kind: 'text', text: '' });
});

test('mapA2APartToGenkit does not corrupt JSON-primitive text (string)', () => {
  const part = { kind: 'text' as const, text: '"hello"' };
  const mapped = mapA2APartToGenkit(part);
  assert.deepStrictEqual(mapped, { text: '"hello"' });
});

test('mapA2APartToGenkit does not corrupt JSON-primitive text (number)', () => {
  const part = { kind: 'text' as const, text: '42' };
  const mapped = mapA2APartToGenkit(part);
  assert.deepStrictEqual(mapped, { text: '42' });
});

test('mapA2APartToGenkit does not corrupt JSON array text', () => {
  const part = { kind: 'text' as const, text: '[1,2,3]' };
  const mapped = mapA2APartToGenkit(part);
  assert.deepStrictEqual(mapped, { text: '[1,2,3]' });
});

test('mapA2APartToGenkit restores toolRequest parts from JSON', () => {
  const original = { toolRequest: { name: 'myTool', input: { x: 1 } } };
  const part = { kind: 'text' as const, text: JSON.stringify(original) };
  const mapped = mapA2APartToGenkit(part);
  assert.deepStrictEqual(mapped, original);
});

test('mapA2APartToGenkit restores toolRequest parts from DataPart', () => {
  const original = { toolRequest: { name: 'myTool', input: { x: 1 } } };
  const part = { kind: 'data' as const, data: original };
  const mapped = mapA2APartToGenkit(part as unknown as A2APart);
  assert.deepStrictEqual(mapped, original);
});

// Multi-turn state continuity

function makeRequestContext(taskId: string, contextId: string, text: string) {
  return {
    taskId,
    contextId,
    userMessage: { parts: [{ kind: 'text' as const, text }] },
  } as unknown as RequestContext;
}

function makeMockEventBus() {
  const events: Record<string, unknown>[] = [];
  return {
    bus: { publish: (e: Record<string, unknown>) => events.push(e), finished: () => {} } as unknown as ExecutionEventBus,
    events,
  };
}

test('SessionFlowAgentExecutor maintains conversation history across turns (no store)', async () => {
  const ai = genkit({});

  const echoFlow = ai.defineSessionFlow(
    { name: 'echoFlowMultiTurn' },
    async (sess, { sendChunk }) => {
      await sess.run(async () => {
        const msgs = sess.session.getMessages();
        sendChunk({ modelChunk: { content: [{ text: `turn ${msgs.length}` }] } });
      });
      const msgs = sess.session.getMessages();
      return { message: msgs[msgs.length - 1] };
    }
  );

  const executor = new SessionFlowAgentExecutor(echoFlow);
  const ctx1 = makeRequestContext('task-1', 'ctx-A', 'first');
  const { bus: bus1, events: events1 } = makeMockEventBus();
  await executor.execute(ctx1, bus1);

  const ctx2 = makeRequestContext('task-2', 'ctx-A', 'second');
  const { bus: bus2, events: events2 } = makeMockEventBus();
  await executor.execute(ctx2, bus2);

  const msgEvents1 = events1.filter((e) => (e as { kind?: string }).kind === 'message');
  const msgEvents2 = events2.filter((e) => (e as { kind?: string }).kind === 'message');
  const turn1Count = parseInt(((msgEvents1[0] as unknown as A2AMessage).parts[0] as { text: string }).text.split(' ')[1]);
  const turn2Count = parseInt(((msgEvents2[0] as unknown as A2AMessage).parts[0] as { text: string }).text.split(' ')[1]);
  assert.equal(turn1Count, 1);
  assert.equal(turn2Count, 2);
});

test('SessionFlowAgentExecutor end-to-end interrupt flow (ask -> input-required -> resume -> completed)', async () => {
  const ai = genkit({});

  const interruptingFlow = ai.defineSessionFlow(
    { name: 'interruptingFlow' },
    async (sess, { sendChunk }) => {
      await sess.run(async (input) => {
        const msgs = sess.session.getMessages();
        const lastMsg = msgs[msgs.length - 1];

        if (lastMsg.role === 'tool') {
          // Resumed with a tool response!
          sendChunk({ modelChunk: { content: [{ text: `Resumed! Tool returned: ${(lastMsg.content[0] as any).toolResponse.output}` }] } });
          return;
        }

        // Interrupt with a tool request
        const requestPart = { toolRequest: { name: 'askUser', input: {}, ref: 'req-1' } };
        sess.session.addMessages([{ role: 'model', content: [requestPart] }]);
        sendChunk({ modelChunk: { content: [requestPart] } });
      });

      const msgs = sess.session.getMessages();
      return { message: msgs[msgs.length - 1] };
    }
  );

  const executor = new SessionFlowAgentExecutor(interruptingFlow);
  const contextId = 'ctx-interrupt-test';
  
  // Turn 1: User sends a message
  const { bus: bus1, events: events1 } = makeMockEventBus();
  await executor.execute(makeRequestContext('t1', contextId, 'Hello, please ask me something.'), bus1);

  const statusEvents1 = events1.filter((e) => (e as { kind?: string }).kind === 'status-update' && (e as any).final === true);
  assert.equal(statusEvents1.length, 1);
  assert.equal((statusEvents1[0] as any).status.state, 'input-required', 'Task should halt requiring input');

  // Check the message sent by the agent (it should contain the tool request)
  const agentMsgEvents1 = events1.filter((e) => (e as { kind?: string }).kind === 'message');
  assert.equal(agentMsgEvents1.length, 1);
  const dataPart = (agentMsgEvents1[0] as any).parts[0];
  assert.equal(dataPart.kind, 'data');
  assert.equal(dataPart.data.toolRequest.name, 'askUser');

  // Turn 2: User provides the requested tool response
  const { bus: bus2, events: events2 } = makeMockEventBus();
  const ctx2 = {
    taskId: 't1',
    contextId,
    userMessage: {
      parts: [{ kind: 'data' as const, data: { toolResponse: { name: 'askUser', ref: 'req-1', output: 'User says YES' } } }],
    },
  } as unknown as RequestContext;
  await executor.execute(ctx2, bus2);

  const statusEvents2 = events2.filter((e) => (e as { kind?: string }).kind === 'status-update' && (e as any).final === true);
  assert.equal(statusEvents2.length, 1);
  assert.equal((statusEvents2[0] as any).status.state, 'completed', 'Task should now complete successfully');

  // Check the final response from the agent
  const agentMsgEvents2 = events2.filter((e) => (e as { kind?: string }).kind === 'message');
  assert.equal(agentMsgEvents2.length, 1);
  const textPart = (agentMsgEvents2[0] as any).parts[0];
  assert.equal(textPart.kind, 'text');
  assert.equal(textPart.text, 'Resumed! Tool returned: User says YES');
});

test('SessionFlowAgentExecutor uses separate histories for different contextIds', async () => {
  const ai = genkit({});

  const counterFlow = ai.defineSessionFlow(
    { name: 'counterFlow' },
    async (sess, { sendChunk }) => {
      await sess.run(async () => {
        const count = sess.session.getMessages().length;
        sendChunk({ modelChunk: { content: [{ text: String(count) }] } });
      });
      const msgs = sess.session.getMessages();
      return { message: msgs[msgs.length - 1] };
    }
  );

  const executor = new SessionFlowAgentExecutor(counterFlow);

  const { bus: busA } = makeMockEventBus();
  await executor.execute(makeRequestContext('t1', 'ctx-X', 'hi'), busA);

  const { bus: busB, events: eventsB } = makeMockEventBus();
  await executor.execute(makeRequestContext('t2', 'ctx-Y', 'hi'), busB);

  // ctx-Y is a fresh conversation — should start at 1 message
  const msgEventsB = eventsB.filter((e) => (e as { kind?: string }).kind === 'message');
  const countY = parseInt(((msgEventsB[0] as unknown as A2AMessage).parts[0] as { text: string }).text);
  assert.equal(countY, 1);
});

test('SessionFlowAgentExecutor passes A2A RequestContext as context to session flow', async () => {
  const ai = genkit({});

  const contextFlow = ai.defineSessionFlow(
    { name: 'contextFlow' },
    async (sess, { context, sendChunk }) => {
      await sess.run(async () => {
        sendChunk({ modelChunk: { role: 'model', content: [{ text: JSON.stringify(context) }] } });
      });
      return { 
        message: { 
          role: 'model', 
          content: [{ text: JSON.stringify(context) }] 
        } 
      };
    }
  );

  const executor = new SessionFlowAgentExecutor(contextFlow);
  
  const mockUser = {
    isAuthenticated: true,
    userName: 'test-user',
  };

  const mockRequestContext = {
    taskId: 't1',
    contextId: 'c1',
    context: {
      user: mockUser,
    },
    userMessage: {
      parts: [{ kind: 'text' as const, text: 'hello' }],
    },
  };
  
  const { bus: bus1, events: events1 } = makeMockEventBus();
  await executor.execute(mockRequestContext as unknown as RequestContext, bus1);

  const msgEvents = events1.filter((e) => (e as { kind?: string }).kind === 'message');
  assert.equal(msgEvents.length, 1);
  
  const textPart = (msgEvents[0] as unknown as A2AMessage).parts[0] as { text: string };
  const receivedContext = JSON.parse(textPart.text);
  
  assert.deepStrictEqual(receivedContext.auth, mockUser);
  assert.equal(receivedContext.a2aRequestContext.taskId, 't1');
  assert.equal(receivedContext.a2aRequestContext.contextId, 'c1');
});

test('SessionFlowAgentExecutor throws when flow has a store (server-managed state)', async () => {
  const ai = genkit({});
  const { InMemorySessionStore } = await import('genkit/beta');

  const storeFlow = ai.defineSessionFlow(
    { name: 'storeFlow', store: new InMemorySessionStore() },
    async (sess, { sendChunk }) => {
      await sess.run(async () => {
        sendChunk({ modelChunk: { content: [{ text: 'hi' }] } });
      });
      return { message: { role: 'model', content: [] } };
    }
  );

  const executor = new SessionFlowAgentExecutor(storeFlow);
  const { bus } = makeMockEventBus();
  await assert.rejects(
    () => executor.execute(makeRequestContext('t1', 'ctx-1', 'hi'), bus),
    /client-managed state/
  );
});

test('SessionFlowAgentExecutor cancelTask stops stream consumption', async () => {
  const ai = genkit({});
  const slowFlow = ai.defineSessionFlow(
    { name: 'slowFlow' },
    async (sess, { sendChunk }) => {
      await sess.run(async () => {
        sendChunk({ modelChunk: { content: [{ text: 'chunk1' }] } });
        sendChunk({ modelChunk: { content: [{ text: 'chunk2' }] } });
      });
      return { message: { role: 'model', content: [] } };
    }
  );

  const executor = new SessionFlowAgentExecutor(slowFlow);

  // Pre-register cancellation before execute runs
  const taskId = 'task-cancel';
  const contextId = 'ctx-cancel';
  (executor as unknown as { cancelledTasks: Set<string> }).cancelledTasks.add(taskId);

  const { bus, events } = makeMockEventBus();
  await executor.execute(makeRequestContext(taskId, contextId, 'go'), bus);

  // No message events should be published because the loop breaks immediately
  const msgEvents = events.filter((e) => (e as { kind?: string }).kind === 'message');
  assert.equal(msgEvents.length, 0);
});

test('SessionFlowAgentExecutor cancelTask publishes canceled status with correct contextId', async () => {
  const ai = genkit({});
  const flow = ai.defineSessionFlow(
    { name: 'cancelFlow' },
    async (sess) => {
      await sess.run(async () => {});
      return { message: { role: 'model', content: [] } };
    }
  );

  const executor = new SessionFlowAgentExecutor(flow);
  // Seed the taskContexts map as execute would
  (executor as unknown as { taskContexts: Map<string, string> }).taskContexts.set('task-99', 'ctx-99');

  const { bus, events } = makeMockEventBus();
  await executor.cancelTask('task-99', bus);

  const statusEvent = events.find((e) => (e as { kind?: string }).kind === 'status-update') as unknown as A2ATaskStatusUpdateEvent;
  assert.ok(statusEvent);
  assert.equal(statusEvent.status.state, 'canceled');
  assert.equal(statusEvent.contextId, 'ctx-99');
});
