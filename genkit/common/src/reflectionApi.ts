import express from 'express';
import * as registry from './registry';

/**
 * Starts a Reflection API that will be used by the Runner to call and control actions and flows.
 *
 * @param port port on which to listen
 */
export function startReflectionApi(port?: number | string | undefined) {
  if (!port) {
    port = process.env.REFLECTION_PORT || 3100;
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
    response.send(registry.listActions());
  });

  // Runs a single action and returns the result (if any).
  api.post('/api/runAction', async (request, response) => {
    const { key, input } = request.body;
    if (!key) {
      return response
        .status(400)
        .json({ message: '`key` is a required field.' });
    }
    console.log(`Running action with key \`${key}\`...`);
    try {
      const result = await registry.lookupAction(key)(input);
      response.send(result);
    } catch (err) {
      const message = `Error running action with key \`${key}\`: ${err}`;
      console.log(message);
      return response.status(500).json({ message });
    }
  });

  const numericPort = Number(port);
  api.listen(numericPort, () => {
    console.log(`Reflection API running on http://localhost:${numericPort}/api`);
  });
}
