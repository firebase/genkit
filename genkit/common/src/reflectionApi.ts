import express from 'express';
import { zodToJsonSchema } from 'zod-to-json-schema';
import { config } from './config.js';
import logging from './logging.js';
import * as registry from './registry.js';

/**
 * Starts a Reflection API that will be used by the Runner to call and control actions and flows.
 * @param port port on which to listen
 */
export async function startReflectionApi(port?: number | undefined) {
  if (!port) {
    port = Number(process.env.GENKIT_REFLECTION_PORT) || 3100;
  }

  const api = express();

  api.use(express.json());
  /*
  api.use(
    validator.middleware({
      apiSpec: path.join(__dirname, '../../api/reflectionApi.yaml'),
      validateRequests: true,
      validateResponses: true,
      ignoreUndocumented: true,
    })
  );
  */

  api.get('/api/__health', (_, response) => {
    response.status(200).send('OK');
  });

  api.get('/api/actions', async (_, response) => {
    logging.debug('Fetching actions.');
    const actions = await registry.listActions();
    const convertedActions = {};
    Object.keys(actions).forEach((key) => {
      const action = actions[key].__action;
      convertedActions[key] = {
        key,
        name: action.name,
        description: action.description,
        metadata: action.metadata,
      };
      if (action.inputSchema) {
        convertedActions[key].inputSchema = zodToJsonSchema(action.inputSchema);
      }
      if (action.outputSchema) {
        convertedActions[key].outputSchema = zodToJsonSchema(
          action.outputSchema
        );
      }
    });
    response.send(convertedActions);
  });

  api.post('/api/runAction', async (request, response) => {
    const { key, input } = request.body;
    logging.debug(`Running action \`${key}\`...`);
    try {
      const action = await registry.lookupAction(key);
      if (!action) {
        response.status(404).send(`action ${key} not found`);
        return;
      }
      const result = await action(input);
      response.send(result);
    } catch (err) {
      const message = `Error running action \`${key}\`: ${err}`;
      logging.error(message);
      return response.status(500).json({ message });
    }
  });

  api.get('/api/envs', async (_, response) => {
    response.json(config.configuredEnvs);
  });

  api.get('/api/envs/:env/traces/:traceId', async (request, response) => {
    const { env, traceId } = request.params;
    logging.debug(`Fetching trace \`${traceId}\` for env \`${env}\`.`);
    const tracestore = await registry.lookupTraceStore(env);
    if (!tracestore) {
      response.status(500).send(`${env} trace store not found`);
      return;
    }
    response.json(await tracestore?.load(traceId));
  });

  api.get('/api/envs/:env/traces', async (request, response) => {
    const { env } = request.params;
    logging.debug(`Fetching traces for env \`${env}\`.`);
    const tracestore = await registry.lookupTraceStore(env);
    if (!tracestore) {
      response.status(500).send(`${env} trace store not found`);
      return;
    }
    response.json(await tracestore.list());
  });

  api.get('/api/envs/:env/flowStates/:flowId', async (request, response) => {
    const { env, flowId } = request.params;
    logging.debug(`Fetching flow state \`${flowId}\` for env \`${env}\`.`);
    const flowStateStore = await registry.lookupFlowStateStore(env);
    if (!flowStateStore) {
      response.status(500).send(`${env} flow state store not found`);
      return;
    }
    response.json(await flowStateStore?.load(flowId));
  });

  api.get('/api/envs/:env/flowStates', async (request, response) => {
    const { env } = request.params;
    logging.debug(`Fetching traces for env \`${env}\`.`);
    const flowStateStore = await registry.lookupFlowStateStore(env);
    if (!flowStateStore) {
      response.status(500).send(`${env} flow state store not found`);
      return;
    }
    response.json(await flowStateStore?.list());
  });

  api.listen(port, () => {
    console.log(`Reflection API running on http://localhost:${port}/api`);
  });
}
