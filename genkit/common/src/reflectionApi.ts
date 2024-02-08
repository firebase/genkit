import express from 'express';
import * as validator from 'express-openapi-validator';
import * as path from 'path';
import { zodToJsonSchema } from 'zod-to-json-schema';
import { getFlowStateStore, getTraceStore, initializeGenkit } from './config';
import logging from './logging';
import * as registry from './registry';

/**
 * Starts a Reflection API that will be used by the Runner to call and control actions and flows.
 * @param port port on which to listen
 */
export function startReflectionApi(port?: number | undefined) {
  if (!port) {
    port = Number(process.env.GENKIT_REFLECTION_PORT) || 3100;
  }
  // When stating reflection API make sure Genkit is initialized from config.
  // We do it asynchronously because we need to give common package to initialize.
  Promise.resolve().then(() => initializeGenkit());

  const api = express();

  api.use(express.json());
  api.use(
    validator.middleware({
      apiSpec: path.join(__dirname, '../../api/reflectionApi.yaml'),
      validateRequests: true,
      validateResponses: true,
      ignoreUndocumented: true,
    })
  );

  // Returns a list of action keys including their type (e.g. text-llm, retriever, flow, etc).
  api.get('/api/actions', (_, response) => {
    const actions = registry.listActions();
    const convertedActions = {};
    Object.keys(actions).forEach((key) => {
      const action = actions[key].__action;
      convertedActions[key] = {
        key,
        name: action.name,
        description: action.description,
      };
      if (action.inputSchema) {
        convertedActions[key].inputSchema = zodToJsonSchema(action.inputSchema);
      }
      if (action.outputSchema) {
        convertedActions[key].outputSchema = zodToJsonSchema(action.outputSchema);
      }
    });
    response.send(convertedActions);
  });

  // Runs a single action and returns the result (if any).
  api.post('/api/runAction', async (request, response) => {
    const { key, input } = request.body;
    console.log(`Running action \`${key}\`...`);
    try {
      const result = await registry.lookupAction(key)(input);
      response.send(result);
    } catch (err) {
      const message = `Error running action \`${key}\`: ${err}`;
      console.log(message);
      return response.status(500).json({ message });
    }
  });

  api.get('/api/env/:env/traces/:traceId', async (req, response) => {
    const { env, traceId } = req.params
    if (env !== 'dev' && env !== 'prod') {
      response.status(400).send(`unsupported env ${env}`)
      return;
    }
    logging.debug(`load trace for env:${env} id:${traceId}`)
    const tracestore = getTraceStore(env);
    response.json(await tracestore.load(traceId));
  });

  api.get('/api/env/:env/traces', async (req, response) => {
    const { env } = req.params
    if (env !== 'dev' && env !== 'prod') {
      response.status(400).send(`unsupported env ${env}`)
      return;
    }
    logging.debug("query traces for env: " + env)
    const tracestore = getTraceStore(env);
    response.json(await tracestore.list());
  });

  api.get('/api/env/:env/flows/:flowId', async (req, response) => {
    const { env, flowId } = req.params
    if (env !== 'dev' && env !== 'prod') {
      response.status(400).send(`unsupported env ${env}`)
      return;
    }
    logging.debug(`load flow for env:${env} id:${flowId}`)
    const flowStateStore = getFlowStateStore(env);
    response.json(await flowStateStore.load(flowId));
  });

  api.get('/api/env/:env/flows', async (req, response) => {
    const { env } = req.params
    if (env !== 'dev' && env !== 'prod') {
      response.status(400).send(`unsupported env ${env}`)
      return;
    }
    logging.debug("query traces for env: " + env)
    const flowStateStore = getFlowStateStore(env);
    response.json(await flowStateStore.list());
  });

  api.listen(port, () => {
    console.log(`Reflection API running on http://localhost:${port}/api`);
  });
}
