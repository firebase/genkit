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

/**
 * Beta Express helpers for serving Genkit agents.
 *
 * ```ts
 * import { serveAgent, serveAgents } from '@genkit-ai/express/beta';
 * ```
 *
 * @module beta
 */

import bodyParser from 'body-parser';
import express from 'express';
import {
  GenkitError,
  type ActionContext,
  type Agent,
  type AgentInput,
  type z,
} from 'genkit/beta';
import type { ContextProvider } from 'genkit/context';
import { expressHandler } from './index.js';

const LITERAL_PATH = /^(\/(?!\.\.?(?:\/|$))[A-Za-z0-9._~-]+)+$/;

/**
 * The `input` that a {@link ServeAgentsOptions.contextProvider} expects: the
 * agent input on the turn route, and the companion action's request on the
 * `getSnapshot`, `waitForSnapshot`, and `abort` routes.
 *
 * It describes the expected shape, not a guaranteed one. The provider runs
 * before schema validation, so `input` can be any JSON value a client sends,
 * or `undefined`.
 *
 * @beta
 */
export type ServeAgentRequest =
  | AgentInput
  | z.infer<
      NonNullable<Agent['getSnapshotDataAction']['__action']['inputSchema']>
    >
  | z.infer<
      NonNullable<Agent['waitForSnapshotAction']['__action']['inputSchema']>
    >
  | z.infer<NonNullable<Agent['abortAgentAction']['__action']['inputSchema']>>;

/**
 * Options for {@link serveAgents}. {@link serveAgent} takes them too.
 *
 * @beta
 */
export interface ServeAgentsOptions<C extends ActionContext = ActionContext> {
  /**
   * Authorizes every route of the agent, companion routes included. Its
   * `input` is a {@link ServeAgentRequest}: the agent input (`AgentInput`) on
   * the turn route, and the companion action's request (`{ snapshotId }` or
   * `{ sessionId }`) on the companion routes. The provider runs before schema
   * validation, so `input` is unvalidated and can be `undefined`, `null`, a
   * string, or any other JSON value.
   *
   * A provider typed for the turn route only, such as
   * `ContextProvider<C, AgentInput>`, does not compile here because the
   * companion routes send it other inputs. Type its input as
   * `ServeAgentRequest`, or leave it untyped (`ContextProvider<C>`).
   *
   * The provider cannot tell the routes apart. It gets no path, and the
   * `getSnapshot`, `waitForSnapshot`, and `abort` inputs share the
   * `{ snapshotId }` shape, so it cannot allow reads but deny aborts. On the
   * turn route it does not see `init.snapshotId`. Check snapshot ownership in
   * the session store, which receives the context, or mount each route with
   * its own provider through {@link expressHandler}.
   */
  contextProvider?: ContextProvider<C, ServeAgentRequest>;
  /**
   * Options for the JSON body parser of the turn route. Used only for requests
   * whose body no earlier middleware has parsed. The companion routes keep the
   * defaults.
   *
   * The default `limit` is body-parser's 100kb. An agent without a store
   * receives its full conversation in every request, so a long conversation
   * fails with HTTP 413 unless the limit is raised, for example
   * `{ limit: '5mb' }`.
   */
  jsonParserOptions?: bodyParser.OptionsJson;
}

/**
 * Options for {@link serveAgent}.
 *
 * @beta
 */
export interface ServeAgentOptions<C extends ActionContext = ActionContext>
  extends ServeAgentsOptions<C> {
  /**
   * Path of the turn route, relative to where the router is mounted. The
   * companion routes nest under it. Defaults to `/{agent name}`.
   *
   * Must be a literal path: one or more `/`-separated segments of
   * `A-Z a-z 0-9 . _ ~ -`, none of them `.` or `..`. Express route patterns
   * (`:param`, `*`, `(`, `?`, `+`) are rejected, and so is an agent name that
   * would form one. Routes match case-sensitively, like action names.
   */
  path?: string;
}

/**
 * Returns an Express router that serves `agent` in the layout that
 * `remoteAgent({ url })` expects by default:
 *
 * - `POST {path}`: runs a turn (`?stream=true` streams). Always mounted.
 * - `POST {path}/getSnapshot` and `POST {path}/waitForSnapshot`: read a
 *   snapshot, or wait for it to settle. Mounted when the agent manages state
 *   on the server (it has a store).
 * - `POST {path}/abort`: aborts a detached turn. Mounted when the agent's
 *   store can signal the running turn.
 *
 * A companion route that the agent does not support is not mounted. To serve
 * it anyway, mount the action with {@link expressHandler}.
 *
 * The router answers `OPTIONS` requests to its routes itself. Mount `cors()`,
 * and other middleware that must see preflight requests, before it.
 *
 * ```ts
 * import { serveAgent } from '@genkit-ai/express/beta';
 *
 * app.use('/api', serveAgent(weatherAgent, { contextProvider }));
 * ```
 *
 * @beta
 */
export function serveAgent<C extends ActionContext = ActionContext>(
  agent: Agent<any>,
  opts?: ServeAgentOptions<C>
): express.Router {
  return agentRouter(
    [{ agent, path: opts?.path ?? `/${agent.__action.name}` }],
    opts,
    {
      caller: 'serveAgent',
      hint: "Pass the 'path' option when the agent name is not a valid path.",
    }
  );
}

/**
 * Returns one Express router that serves each agent at `/{agent name}`, with
 * the routes that {@link serveAgent} mounts for it. One `contextProvider`
 * covers every route of every agent. For a custom path, or a provider per
 * agent, use {@link serveAgent}.
 *
 * Throws `INVALID_ARGUMENT` if two agents would serve the same route. The check
 * covers only the agents in this call, not routes that other routers mount.
 * An empty list returns a router with no routes.
 *
 * ```ts
 * import { serveAgents } from '@genkit-ai/express/beta';
 *
 * app.use('/api', serveAgents([weatherAgent, researchAgent], { contextProvider }));
 * ```
 *
 * @beta
 */
export function serveAgents<C extends ActionContext = ActionContext>(
  agents: Agent<any>[],
  opts?: ServeAgentsOptions<C>
): express.Router {
  return agentRouter(
    agents.map((agent) => ({ agent, path: `/${agent.__action.name}` })),
    opts,
    {
      caller: 'serveAgents',
      hint: "Serve an agent whose name is not a valid path with serveAgent and its 'path' option.",
    }
  );
}

function agentRouter<C extends ActionContext>(
  entries: { agent: Agent<any>; path: string }[],
  opts: ServeAgentsOptions<C> | undefined,
  errors: { caller: string; hint: string }
): express.Router {
  const parseTurnJson = parseUnlessRead(
    bodyParser.json(opts?.jsonParserOptions)
  );
  const parseJson = parseUnlessRead(bodyParser.json());
  // expressHandler types the provider input as the Zod schema, not the value.
  const contextProvider: ContextProvider<C> | undefined = opts?.contextProvider;
  const handlerOpts = { contextProvider };

  const routes = new Map<
    string,
    [express.RequestHandler, express.RequestHandler]
  >();
  const add = (
    route: string,
    parse: express.RequestHandler,
    handler: express.RequestHandler
  ) => {
    if (routes.has(route)) {
      throw new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: `${errors.caller}: more than one agent serves the path '${route}'.`,
      });
    }
    routes.set(route, [parse, handler]);
  };

  for (const { agent, path } of entries) {
    if (!LITERAL_PATH.test(path)) {
      throw new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: `${errors.caller}: invalid path '${path}'. It must be one or more '/'-separated segments of the characters A-Z a-z 0-9 . _ ~ -, none of them '.' or '..', and must not end with '/'. ${errors.hint}`,
      });
    }
    const capabilities = agent.__action.metadata?.agent;
    add(path, parseTurnJson, expressHandler(agent, handlerOpts));
    if (capabilities?.stateManagement === 'server') {
      add(
        `${path}/getSnapshot`,
        parseJson,
        expressHandler(agent.getSnapshotDataAction, handlerOpts)
      );
      add(
        `${path}/waitForSnapshot`,
        parseJson,
        expressHandler(agent.waitForSnapshotAction, handlerOpts)
      );
    }
    if (capabilities?.abortable === true) {
      add(
        `${path}/abort`,
        parseJson,
        expressHandler(agent.abortAgentAction, handlerOpts)
      );
    }
  }

  const router = express.Router({ caseSensitive: true, strict: false });
  for (const [route, handlers] of routes) router.post(route, ...handlers);
  return router;
}

function parseUnlessRead(
  parser: express.RequestHandler
): express.RequestHandler {
  // Not `req.body`: body-parser 1.x sets it to `{}` for content types it skips.
  return (req, res, next) => {
    if (req.readableEnded) {
      next();
      return;
    }
    parser(req, res, next);
  };
}
