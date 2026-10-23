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
 * The `input` a {@link ServeAgentsOptions.contextProvider} receives: the agent
 * input on the turn route, or the companion action's request.
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
   * Authorizes every mounted route. It runs before validation, so `input` may
   * be any JSON value.
   */
  contextProvider?: ContextProvider<C, ServeAgentRequest>;
  /** JSON body parser options for the turn route. Default limit: 100kb. */
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
   * Literal path of the turn route, with no route patterns. Defaults to
   * `/{agent name}`.
   */
  path?: string;
}

/**
 * Returns an Express router that serves `agent` in the layout `remoteAgent`
 * expects. Companion routes are mounted only when the agent supports them:
 *
 * - `POST {path}`: runs a turn.
 * - `POST {path}/getSnapshot`, `/waitForSnapshot`: agents with a store.
 * - `POST {path}/abort`: stores that can signal the running turn.
 *
 * Mount `cors()` before the router, which answers `OPTIONS` itself.
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
 * Returns one Express router that serves each agent at `/{agent name}`, like
 * {@link serveAgent}. Throws if two agents in this call serve the same route.
 *
 * ```ts
 * import { serveAgents } from '@genkit-ai/express/beta';
 *
 * app.use('/api', serveAgents([weatherAgent, researchAgent]));
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
