import { test } from 'node:test';
import * as assert from 'node:assert';
import { SessionFlowAgentExecutor, defineA2ASessionFlow, mapGenkitPartToA2A, mapA2APartToGenkit } from '../src/index.js';
import { genkit } from 'genkit/beta';
import { RequestContext, ExecutionEventBus } from '@a2a-js/sdk/server';

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

test('mapGenkitPartToA2A falls back to JSON for complex parts', () => {
  const part = { custom: { foo: 'bar' } };
  const mapped = mapGenkitPartToA2A(part);
  assert.strictEqual(mapped.kind, 'text');
  assert.strictEqual(mapped.text, JSON.stringify(part));
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

test('mapA2APartToGenkit restores complex parts from JSON', () => {
  const originalPart = { toolCall: { name: 'myTool', args: {} } };
  const part = { kind: 'text', text: JSON.stringify(originalPart) } as const;
  const mapped = mapA2APartToGenkit(part);
  assert.deepStrictEqual(mapped, originalPart);
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
  
  assert.equal(publishedEvents.length, 1);
  assert.equal(publishedEvents[0].kind, 'message');
  const parts = publishedEvents[0].parts as { kind: string, text: string }[];
  assert.equal(parts[0].text, 'response');
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
  
  assert.equal(publishedEvents.length, 1);
  assert.equal(publishedEvents[0].kind, 'status-update');
  const status = publishedEvents[0].status as { state: string };
  assert.equal(status.state, 'working');
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
  
  assert.equal(publishedEvents.length, 1);
  assert.equal(publishedEvents[0].kind, 'artifact-update');
  const artifact = publishedEvents[0].artifact as { artifactId: string };
  assert.equal(artifact.artifactId, 'myArtifact');
});

test('defineA2ASessionFlow executes and maps incoming stream', async () => {
  const ai = genkit({});
  
  const mockClient = {
    sendMessageStream: (params: Record<string, unknown>) => {
      return (async function* () {
        yield { kind: 'message', parts: [{ kind: 'text', text: 'a2a response' }] };
        yield { kind: 'status-update', status: { state: 'a2a working' } };
      })();
    }
  };
  
  const mockFactory = {
    createFromUrl: async (url: string) => mockClient
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
  assert.equal(secondChunk.status, 'a2a working');
  const thirdChunk = chunks[2] as { turnEnd: { snapshotId: string } };
  assert.ok(thirdChunk.turnEnd);
});
