import express from 'express';
import { zodToJsonSchema } from "zod-to-json-schema";
import * as registry from './registry';
import { JSONSchema7Type } from 'json-schema';

// TODO: Replace this with a build-time dependency that comes from genkit-tools.
export interface ActionSchema {
  key: string;
  name: string;
  description?: string;
  input?: JSONSchema7Type;
  output?: JSONSchema7Type;
}

/**
 * Starts a Reflection API that will be used by the Runner to call and control actions and flows.
 * @param port port on which to listen
 */
export function startReflectionApi(port?: number | undefined) {
  if (!port) {
    port = Number(process.env.GENKIT_REFLECTION_PORT) || 3100;
  }
  const api = express();
  api.use(express.json());

  // Returns the status of the API.
  api.get('/api/status', (request, response) => {
    const uptime = process.uptime();
    response.json({
      status: 'OK',
      timestamp: new Date(),
      uptime: `${Math.floor(uptime / 60)} minutes, ${Math.floor(
        uptime % 60
      )} seconds`,
    });
  });

  // Returns a list of action keys including their type (e.g. text-llm, retriever, flow, etc).
  api.get('/api/actions', (_, response) => {
    const actions = registry.listActions();
    const convertedActions: Record<string, ActionSchema> = {};
    Object.keys(actions).forEach((key) => {
      const action = actions[key].__action;
      convertedActions[key] = {
        key,
        name: action.name,
        description: action.description,
      };
      if (action.inputSchema) {
        convertedActions[key].input = zodToJsonSchema(action.inputSchema) as JSONSchema7Type;
      }
      if (action.outputSchema) {
        convertedActions[key].output = zodToJsonSchema(action.outputSchema) as JSONSchema7Type;
      }
    });
    response.send(convertedActions);
  });

  // Runs a single action and returns the result (if any).
  api.post('/api/runAction', async (request, response) => {
    const { key, input } = request.body;
    if (!key) {
      return response
        .status(400)
        .json({ message: '`key` is a required field.' });
    }
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

  api.listen(port, () => {
    console.log(`Reflection API running on http://localhost:${port}/api`);
  });
}
