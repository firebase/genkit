/**
 * Copyright 2026 Google LLC
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

import * as assert from 'assert';
import cors from 'cors';
import express from 'express';
import { UserFacingError } from 'genkit';
import {
  InMemorySessionStore,
  genkit,
  type ActionContext,
  type Agent,
  type AgentInput,
  type AgentInputSchema,
  type GenkitBeta,
  type SessionStore,
} from 'genkit/beta';
import { remoteAgent } from 'genkit/beta/client';
import type { ContextProvider, RequestData } from 'genkit/context';
import getPort from 'get-port';
import type * as http from 'http';
import { afterEach, beforeEach, describe, it } from 'node:test';
import {
  serveAgent,
  serveAgents,
  type ServeAgentRequest,
} from '../src/beta.js';

const contextProvider: ContextProvider = (req) => {
  if (req.headers['authorization'] !== 'open sesame') {
    throw new UserFacingError('PERMISSION_DENIED', 'not authorized');
  }
  return { auth: { user: 'Ali Baba' } };
};

/** A store that cannot signal a running turn, so its agent is not abortable. */
function storeWithoutSignals(): SessionStore {
  const inner = new InMemorySessionStore();
  return {
    getSnapshot: (opts) => inner.getSnapshot(opts),
    saveSnapshot: (id, mutator, options) =>
      inner.saveSnapshot(id, mutator, options),
  };
}

function defineEchoAgent(
  ai: GenkitBeta,
  name: string,
  store?: SessionStore,
  gate?: Promise<void>
): Agent {
  return ai.defineCustomAgent(
    { name, store },
    async (sess, { abortSignal }) => {
      const aborted = new Promise<void>((resolve) =>
        abortSignal?.addEventListener('abort', () => resolve())
      );
      await sess.run(async (input) => {
        await Promise.race([gate, aborted]);
        sess.addMessages([
          {
            role: 'model',
            content: [{ text: `echo: ${input.message?.content[0].text}` }],
          },
        ]);
      });
      return { artifacts: [], message: sess.session.getMessages().at(-1) };
    }
  );
}

/**
 * Whether `url` reaches a mounted route. Express answers an unmatched route
 * with its own HTML 404, while a mounted Genkit route answers in JSON.
 */
async function isMounted(url: string): Promise<boolean> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: {} }),
  });
  const body = await res.text();
  return !(res.status === 404 && body.includes('Cannot POST'));
}

describe('serveAgent', () => {
  let server: http.Server | undefined;
  let ai: GenkitBeta;

  beforeEach(() => {
    ai = genkit({});
  });

  afterEach(async () => {
    const closing = server;
    server = undefined;
    if (!closing) return;
    closing.closeAllConnections();
    await new Promise<void>((resolve, reject) =>
      closing.close((err) => (err ? reject(err) : resolve()))
    );
  });

  async function listen(app: express.Express): Promise<string> {
    const port = await getPort();
    await new Promise<void>((resolve) => {
      server = app.listen(port, resolve);
    });
    return `http://localhost:${port}`;
  }

  async function serve(
    router: express.Router,
    appMiddleware: express.RequestHandler[] = []
  ): Promise<string> {
    const app = express();
    for (const middleware of appMiddleware) app.use(middleware);
    app.use('/api', router);
    return listen(app);
  }

  describe('route set', () => {
    it('mounts only the turn route for a client-managed agent', async () => {
      const agent = defineEchoAgent(ai, 'clientAgent');
      const base = await serve(serveAgent(agent));

      assert.strictEqual(await isMounted(`${base}/api/clientAgent`), true);
      assert.strictEqual(
        await isMounted(`${base}/api/clientAgent/getSnapshot`),
        false
      );
      assert.strictEqual(
        await isMounted(`${base}/api/clientAgent/waitForSnapshot`),
        false
      );
      assert.strictEqual(
        await isMounted(`${base}/api/clientAgent/abort`),
        false
      );
    });

    it('mounts the snapshot routes but not abort for a store that cannot signal', async () => {
      const agent = defineEchoAgent(ai, 'storeAgent', storeWithoutSignals());
      const base = await serve(serveAgent(agent));

      assert.strictEqual(await isMounted(`${base}/api/storeAgent`), true);
      assert.strictEqual(
        await isMounted(`${base}/api/storeAgent/getSnapshot`),
        true
      );
      assert.strictEqual(
        await isMounted(`${base}/api/storeAgent/waitForSnapshot`),
        true
      );
      assert.strictEqual(
        await isMounted(`${base}/api/storeAgent/abort`),
        false
      );
    });

    it('mounts every route for an abortable agent', async () => {
      const agent = defineEchoAgent(
        ai,
        'abortableAgent',
        new InMemorySessionStore()
      );
      const base = await serve(serveAgent(agent));

      for (const suffix of ['', '/getSnapshot', '/waitForSnapshot', '/abort']) {
        assert.strictEqual(
          await isMounted(`${base}/api/abortableAgent${suffix}`),
          true,
          `expected /api/abortableAgent${suffix} to be mounted`
        );
      }
    });

    it('treats missing capability metadata as unsupported', async () => {
      const agent = defineEchoAgent(
        ai,
        'bareMetaAgent',
        new InMemorySessionStore()
      );
      delete agent.__action.metadata!.agent;
      const base = await serve(serveAgent(agent));

      assert.strictEqual(await isMounted(`${base}/api/bareMetaAgent`), true);
      for (const suffix of ['/getSnapshot', '/waitForSnapshot', '/abort']) {
        assert.strictEqual(
          await isMounted(`${base}/api/bareMetaAgent${suffix}`),
          false,
          `expected /api/bareMetaAgent${suffix} not to be mounted`
        );
      }
    });

    it('treats unrecognized capability metadata as unsupported', async () => {
      const agent = defineEchoAgent(ai, 'oddAgent', new InMemorySessionStore());
      agent.__action.metadata!.agent = {
        stateManagement: 'SERVER',
        abortable: 'yes',
      };
      const base = await serve(serveAgent(agent));

      assert.strictEqual(await isMounted(`${base}/api/oddAgent`), true);
      assert.strictEqual(
        await isMounted(`${base}/api/oddAgent/getSnapshot`),
        false
      );
      assert.strictEqual(
        await isMounted(`${base}/api/oddAgent/waitForSnapshot`),
        false
      );
      assert.strictEqual(await isMounted(`${base}/api/oddAgent/abort`), false);
    });
  });

  describe('path', () => {
    it('serves the agent at a custom path', async () => {
      const agent = defineEchoAgent(
        ai,
        'pathAgent',
        new InMemorySessionStore()
      );
      const base = await serve(serveAgent(agent, { path: '/v1/weather' }));

      assert.strictEqual(await isMounted(`${base}/api/pathAgent`), false);
      for (const suffix of ['', '/getSnapshot', '/waitForSnapshot', '/abort']) {
        assert.strictEqual(
          await isMounted(`${base}/api/v1/weather${suffix}`),
          true,
          `expected /api/v1/weather${suffix} to be mounted`
        );
      }

      const chat = remoteAgent({ url: `${base}/api/v1/weather` }).chat();
      const res = await chat.send('hi');
      assert.strictEqual(res.text, 'echo: hi');
    });

    for (const path of [
      '/',
      '',
      'weather',
      '/weather/',
      '//weather',
      '/agent:v1',
      '/a*b',
      '/weather(v1)',
      '/weather?',
      '/weather+',
      '/.',
      '/..',
      '/a/../b',
      '/a/.',
      '/../weather',
    ]) {
      it(`rejects the path '${path}'`, () => {
        const agent = defineEchoAgent(ai, 'badPathAgent');
        assert.throws(
          () => serveAgent(agent, { path }),
          (e: Error) =>
            e.message.includes('INVALID_ARGUMENT') &&
            e.message.includes(`invalid path '${path}'`)
        );
      });
    }

    it('rejects an agent name that is not a literal path', async () => {
      const agent = defineEchoAgent(ai, 'agent:v1');
      assert.throws(() => serveAgent(agent), /invalid path '\/agent:v1'/);
    });

    it('rejects an agent name that is a dot segment', () => {
      const agent = defineEchoAgent(ai, '..');
      assert.throws(() => serveAgent(agent), /invalid path '\/\.\.'/);
    });

    it('routes agent names case-sensitively', async () => {
      const upper = defineEchoAgent(ai, 'Foo');
      const lower = ai.defineCustomAgent({ name: 'foo' }, async (sess) => {
        await sess.run(async () => {
          sess.addMessages([{ role: 'model', content: [{ text: 'lower' }] }]);
        });
        return { artifacts: [], message: sess.session.getMessages().at(-1) };
      });
      const app = express();
      app.use('/api', serveAgent(upper), serveAgent(lower));
      const base = await listen(app);

      const fromUpper = await remoteAgent({ url: `${base}/api/Foo` })
        .chat()
        .send('hi');
      assert.strictEqual(fromUpper.text, 'echo: hi');
      const fromLower = await remoteAgent({ url: `${base}/api/foo` })
        .chat()
        .send('hi');
      assert.strictEqual(fromLower.text, 'lower');
      assert.strictEqual(await isMounted(`${base}/api/FOO`), false);
      assert.strictEqual(await isMounted(`${base}/api/FOO/`), false);
    });

    it('serves the turn route with a trailing slash', async () => {
      const agent = defineEchoAgent(ai, 'slashAgent');
      const base = await serve(serveAgent(agent));

      const res = await remoteAgent({ url: `${base}/api/slashAgent/` })
        .chat()
        .send('hi');
      assert.strictEqual(res.text, 'echo: hi');
    });

    it('accepts an agent name with dots, dashes, and underscores', async () => {
      const agent = defineEchoAgent(ai, 'my-agent_v1.2');
      const base = await serve(serveAgent(agent));

      const res = await remoteAgent({ url: `${base}/api/my-agent_v1.2` })
        .chat()
        .send('hi');
      assert.strictEqual(res.text, 'echo: hi');
    });
  });

  describe('contextProvider', () => {
    let base: string;

    beforeEach(async () => {
      const agent = defineEchoAgent(
        ai,
        'authAgent',
        new InMemorySessionStore()
      );
      base = await serve(serveAgent(agent, { contextProvider }));
    });

    for (const suffix of ['', '/getSnapshot', '/waitForSnapshot', '/abort']) {
      it(`rejects an unauthorized request to /api/authAgent${suffix}`, async () => {
        const res = await fetch(`${base}/api/authAgent${suffix}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ data: { snapshotId: 'any' } }),
        });
        assert.strictEqual(res.status, 403);
        assert.deepStrictEqual(await res.json(), {
          status: 'PERMISSION_DENIED',
          message: 'not authorized',
        });
      });
    }

    it('rejects an unauthorized streaming turn', async () => {
      const res = await fetch(`${base}/api/authAgent?stream=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: {} }),
      });
      assert.strictEqual(res.status, 403);
      assert.deepStrictEqual(await res.json(), {
        status: 'PERMISSION_DENIED',
        message: 'not authorized',
      });
    });

    it('types the provider input as the requests the routes receive', () => {
      const agent = defineEchoAgent(ai, 'typedAuthAgent');
      const inputs: ServeAgentRequest[] = [
        { message: { role: 'user', content: [{ text: 'hi' }] } },
        { snapshotId: 's1', metadataOnly: true },
        { sessionId: 'session1' },
      ];
      const byInput = ({ input }: RequestData<ServeAgentRequest>) => ({
        auth: { snapshotId: 'snapshotId' in input ? input.snapshotId : null },
      });
      const wrongInput = (_req: RequestData<{ flowArg: string }>) => ({});

      assert.strictEqual(inputs.length, 3);
      serveAgent(agent, { contextProvider: byInput });
      // @ts-expect-error The routes never receive a flow's input.
      serveAgent(agent, { contextProvider: wrongInput });
    });

    it('rejects a provider typed for the turn route only', () => {
      const agent = defineEchoAgent(ai, 'turnTypedAuthAgent');
      const byValue: ContextProvider<ActionContext, AgentInput> = () => ({});
      const bySchema: ContextProvider<
        ActionContext,
        typeof AgentInputSchema
      > = () => ({});
      const untyped: ContextProvider = () => ({});

      // @ts-expect-error The companion routes send `{ snapshotId }`.
      serveAgent(agent, { contextProvider: byValue });
      // @ts-expect-error The companion routes send `{ snapshotId }`.
      serveAgents([agent], { contextProvider: bySchema });
      serveAgent(agent, { contextProvider: untyped });
      serveAgents([agent], { contextProvider: untyped });
    });

    it('runs a turn and reads its snapshot when authorized', async () => {
      const agent = remoteAgent({
        url: `${base}/api/authAgent`,
        headers: { authorization: 'open sesame' },
      });
      const res = await agent.chat().send('hi');
      assert.strictEqual(res.text, 'echo: hi');
      assert.ok(res.snapshotId);

      const snapshot = await agent.getSnapshot(res.snapshotId);
      assert.strictEqual(snapshot?.snapshotId, res.snapshotId);
    });
  });

  describe('body parsing', () => {
    it('parses JSON bodies without app-level middleware', async () => {
      const agent = defineEchoAgent(ai, 'bareAgent');
      const base = await serve(serveAgent(agent));

      const res = await remoteAgent({ url: `${base}/api/bareAgent` })
        .chat()
        .send('hi');
      assert.strictEqual(res.text, 'echo: hi');
    });

    it('uses a body the app has already parsed', async () => {
      const agent = defineEchoAgent(ai, 'parsedAgent');
      const base = await serve(serveAgent(agent), [express.json()]);

      const res = await remoteAgent({ url: `${base}/api/parsedAgent` })
        .chat()
        .send('hi');
      assert.strictEqual(res.text, 'echo: hi');
    });

    for (const [name, middleware] of [
      ['urlencoded', express.urlencoded({ extended: false })],
      ['text', express.text()],
      ['raw', express.raw()],
    ] as const) {
      it(`parses JSON bodies after an app-level ${name} parser`, async () => {
        const agent = defineEchoAgent(ai, `${name}Agent`);
        const base = await serve(serveAgent(agent), [middleware]);

        const res = await remoteAgent({ url: `${base}/api/${name}Agent` })
          .chat()
          .send('hi');
        assert.strictEqual(res.text, 'echo: hi');
      });
    }

    it('uses a body that app middleware read from the stream', async () => {
      const agent = defineEchoAgent(ai, 'streamReadAgent');
      const readBody: express.RequestHandler = async (req, _res, next) => {
        let raw = '';
        for await (const chunk of req) raw += chunk;
        req.body = JSON.parse(raw);
        next();
      };
      const base = await serve(serveAgent(agent), [readBody]);

      const res = await remoteAgent({ url: `${base}/api/streamReadAgent` })
        .chat()
        .send('hi');
      assert.strictEqual(res.text, 'echo: hi');
    });

    describe('body size limit', () => {
      const largeTurn = JSON.stringify({
        data: {
          message: { role: 'user', content: [{ text: 'x'.repeat(200_000) }] },
        },
        init: {},
      });

      function postLargeTurn(url: string): Promise<Response> {
        return fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: largeTurn,
        });
      }

      it('rejects a turn body over 100kb by default', async () => {
        const agent = defineEchoAgent(ai, 'smallLimitAgent');
        const base = await serve(serveAgent(agent));

        const res = await postLargeTurn(`${base}/api/smallLimitAgent`);
        assert.strictEqual(res.status, 413);
      });

      it('accepts a larger turn body with jsonParserOptions', async () => {
        const agent = defineEchoAgent(ai, 'largeLimitAgent');
        const base = await serve(
          serveAgent(agent, { jsonParserOptions: { limit: '1mb' } })
        );

        const res = await postLargeTurn(`${base}/api/largeLimitAgent`);
        assert.strictEqual(res.status, 200);
        const body = await res.json();
        assert.ok(body.result.message.content[0].text.startsWith('echo: xxx'));
      });

      for (const suffix of ['/getSnapshot', '/waitForSnapshot', '/abort']) {
        it(`keeps the default limit on ${suffix}`, async () => {
          const agent = defineEchoAgent(
            ai,
            'companionLimitAgent',
            new InMemorySessionStore()
          );
          const base = await serve(
            serveAgent(agent, { jsonParserOptions: { limit: '1mb' } })
          );

          const res = await fetch(`${base}/api/companionLimitAgent${suffix}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              data: { snapshotId: 'x'.repeat(200_000) },
            }),
          });
          assert.strictEqual(res.status, 413);
        });
      }

      it('leaves the limit to a JSON parser the app runs first', async () => {
        const agent = defineEchoAgent(ai, 'appLimitAgent');
        const base = await serve(
          serveAgent(agent, { jsonParserOptions: { limit: '1mb' } }),
          [express.json()]
        );

        const res = await postLargeTurn(`${base}/api/appLimitAgent`);
        assert.strictEqual(res.status, 413);
      });
    });

    it('does not parse bodies for routes it does not serve', async () => {
      const agent = defineEchoAgent(ai, 'scopedAgent');
      const app = express();
      let otherBody: unknown = 'unset';
      app.use('/api', serveAgent(agent));
      app.post('/api/other', (req, res) => {
        otherBody = req.body;
        res.status(204).end();
      });
      const base = await listen(app);

      await fetch(`${base}/api/other`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: 1 }),
      });
      assert.strictEqual(otherBody, undefined);
    });
  });

  describe('CORS', () => {
    it('answers preflights with the headers of cors() mounted before it', async () => {
      const agent = defineEchoAgent(
        ai,
        'corsAgent',
        new InMemorySessionStore()
      );
      const base = await serve(serveAgent(agent), [cors()]);

      for (const suffix of ['', '/getSnapshot']) {
        const res = await fetch(`${base}/api/corsAgent${suffix}`, {
          method: 'OPTIONS',
          headers: {
            Origin: 'https://app.example',
            'Access-Control-Request-Method': 'POST',
          },
        });
        assert.strictEqual(res.status, 204);
        assert.strictEqual(res.headers.get('access-control-allow-origin'), '*');
      }
    });
  });

  describe('serveAgents', () => {
    it('serves each agent with its own route set and one contextProvider', async () => {
      const agents = [
        defineEchoAgent(ai, 'clientAgent'),
        defineEchoAgent(ai, 'storeAgent', storeWithoutSignals()),
        defineEchoAgent(ai, 'abortableAgent', new InMemorySessionStore()),
      ];
      const base = await serve(serveAgents(agents, { contextProvider }));

      const expected: Record<string, string[]> = {
        clientAgent: [''],
        storeAgent: ['', '/getSnapshot', '/waitForSnapshot'],
        abortableAgent: ['', '/getSnapshot', '/waitForSnapshot', '/abort'],
      };
      for (const [name, mounted] of Object.entries(expected)) {
        for (const suffix of [
          '',
          '/getSnapshot',
          '/waitForSnapshot',
          '/abort',
        ]) {
          const url = `${base}/api/${name}${suffix}`;
          if (!mounted.includes(suffix)) {
            assert.strictEqual(await isMounted(url), false, url);
            continue;
          }
          const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data: { snapshotId: 'any' } }),
          });
          assert.strictEqual(res.status, 403, url);
        }
      }
    });

    it('serves several agents to remoteAgent', async () => {
      const first = defineEchoAgent(
        ai,
        'firstAgent',
        new InMemorySessionStore()
      );
      const second = ai.defineCustomAgent(
        { name: 'secondAgent' },
        async (sess) => {
          await sess.run(async () => {
            sess.addMessages([
              { role: 'model', content: [{ text: 'second' }] },
            ]);
          });
          return { artifacts: [], message: sess.session.getMessages().at(-1) };
        }
      );
      const base = await serve(serveAgents([first, second]));

      const firstAgent = remoteAgent({ url: `${base}/api/firstAgent` });
      const fromFirst = await firstAgent.chat().send('hi');
      assert.strictEqual(fromFirst.text, 'echo: hi');
      const snapshot = await firstAgent.getSnapshot(fromFirst.snapshotId!);
      assert.strictEqual(snapshot?.snapshotId, fromFirst.snapshotId);

      const fromSecond = await remoteAgent({ url: `${base}/api/secondAgent` })
        .chat()
        .send('hi');
      assert.strictEqual(fromSecond.text, 'second');
    });

    it('serves alongside a serveAgent router in one mount', async () => {
      const clientAgent = defineEchoAgent(ai, 'clientAgent');
      const abortableAgent = defineEchoAgent(
        ai,
        'abortableAgent',
        new InMemorySessionStore()
      );
      const customAgent = defineEchoAgent(
        ai,
        'customAgent',
        storeWithoutSignals()
      );
      const app = express();
      app.use(cors());
      app.use(
        '/api',
        serveAgents([clientAgent, abortableAgent]),
        serveAgent(customAgent, { path: '/custom' })
      );
      const base = await listen(app);

      const fromClient = await remoteAgent({ url: `${base}/api/clientAgent` })
        .chat()
        .send('one');
      assert.strictEqual(fromClient.text, 'echo: one');

      const abortable = remoteAgent({ url: `${base}/api/abortableAgent` });
      const fromAbortable = await abortable.chat().send('two');
      assert.strictEqual(fromAbortable.text, 'echo: two');
      const snapshot = await abortable.getSnapshot(fromAbortable.snapshotId!);
      assert.strictEqual(snapshot?.snapshotId, fromAbortable.snapshotId);
      const loaded = await abortable.loadChat({
        snapshotId: fromAbortable.snapshotId!,
      });
      assert.deepStrictEqual(
        loaded.messages.map((m) => m.content[0].text),
        ['two', 'echo: two']
      );

      const fromCustom = await remoteAgent({ url: `${base}/api/custom` })
        .chat()
        .send('three');
      assert.strictEqual(fromCustom.text, 'echo: three');

      for (const path of ['/api/custom', '/api/custom/getSnapshot']) {
        const res = await fetch(`${base}${path}`, {
          method: 'OPTIONS',
          headers: {
            Origin: 'https://app.example',
            'Access-Control-Request-Method': 'POST',
          },
        });
        assert.strictEqual(res.status, 204, path);
        assert.strictEqual(
          res.headers.get('access-control-allow-origin'),
          '*',
          path
        );
      }
    });

    it('rejects two agents with the same name', () => {
      const first = defineEchoAgent(ai, 'twinAgent');
      const second = defineEchoAgent(genkit({}), 'twinAgent');
      assert.throws(
        () => serveAgents([first, second]),
        (e: Error) =>
          e.message.includes('INVALID_ARGUMENT') &&
          e.message.includes("more than one agent serves the path '/twinAgent'")
      );
    });

    it('rejects an agent whose turn route is a companion route of another', () => {
      const parent = defineEchoAgent(ai, 'parent', new InMemorySessionStore());
      const child = defineEchoAgent(ai, 'parent/getSnapshot');
      assert.throws(
        () => serveAgents([parent, child]),
        /more than one agent serves the path '\/parent\/getSnapshot'/
      );
    });

    it('returns a router with no routes for an empty list', async () => {
      const app = express();
      app.use('/api', serveAgents([]));
      app.post('/api/next', (_req, res) => {
        res.status(204).end();
      });
      const base = await listen(app);

      const res = await fetch(`${base}/api/next`, { method: 'POST' });
      assert.strictEqual(res.status, 204);
      assert.strictEqual(await isMounted(`${base}/api/anyAgent`), false);
    });

    for (const name of ['agent:v1', '..']) {
      it(`rejects the agent name '${name}'`, () => {
        const valid = defineEchoAgent(ai, 'validAgent');
        const invalid = defineEchoAgent(ai, name);
        assert.throws(
          () => serveAgents([valid, invalid]),
          (e: Error) =>
            e.message.includes('INVALID_ARGUMENT') &&
            e.message.includes(`serveAgents: invalid path '/${name}'`)
        );
      });
    }
  });

  describe('with remoteAgent', () => {
    let base: string;
    let requests: string[];
    let releaseTurn: () => void;

    beforeEach(async () => {
      requests = [];
      const gate = new Promise<void>((resolve) => (releaseTurn = resolve));
      const chatAgent = defineEchoAgent(
        ai,
        'chatAgent',
        new InMemorySessionStore()
      );
      const taskAgent = defineEchoAgent(
        ai,
        'taskAgent',
        new InMemorySessionStore(),
        gate
      );
      const app = express();
      app.use((req, _res, next) => {
        requests.push(req.path);
        next();
      });
      app.use('/api', serveAgent(chatAgent), serveAgent(taskAgent));
      base = await listen(app);
    });

    afterEach(() => {
      releaseTurn();
    });

    it('chats and reloads the chat from its snapshot', async () => {
      const agent = remoteAgent({ url: `${base}/api/chatAgent` });
      const chat = agent.chat();
      await chat.send('one');
      const res = await chat.send('two');
      assert.strictEqual(res.text, 'echo: two');

      const loaded = await agent.loadChat({ snapshotId: res.snapshotId! });
      assert.deepStrictEqual(
        loaded.messages.map((m) => m.content[0].text),
        ['one', 'echo: one', 'two', 'echo: two']
      );
    });

    it('waits for a detached task through waitForSnapshot without polling', async () => {
      const agent = remoteAgent({ url: `${base}/api/taskAgent` });
      const task = await agent.chat().detach('long job');

      const waits = () =>
        requests.filter((p) => p === '/api/taskAgent/waitForSnapshot').length;
      let done = false;
      const settled = task.wait().finally(() => (done = true));
      const deadline = Date.now() + 5_000;
      while (waits() === 0) {
        if (Date.now() > deadline) {
          assert.fail('the client never called /waitForSnapshot');
        }
        await new Promise((resolve) => setTimeout(resolve, 5));
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
      assert.strictEqual(waits(), 1, 'one wait request stays open');
      assert.strictEqual(done, false);

      releaseTurn();
      const snapshot = await settled;

      assert.strictEqual(snapshot.status, 'completed');
      assert.strictEqual(waits(), 1);
      assert.ok(!requests.includes('/api/taskAgent/getSnapshot'));
    });

    it('aborts a detached task', async () => {
      const agent = remoteAgent({ url: `${base}/api/taskAgent` });
      const task = await agent.chat().detach('long job');

      assert.strictEqual(await task.abort(), 'pending');
      const snapshot = await task.wait();
      assert.strictEqual(snapshot.status, 'aborted');
      assert.ok(requests.includes('/api/taskAgent/abort'));
    });
  });
});
