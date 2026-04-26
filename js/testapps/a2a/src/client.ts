import { defineA2ASessionFlow } from '@genkit-ai/a2a';
import { z } from 'genkit';
import { ai } from './genkit.js';

// 1. Define Genkit Session Flow consuming A2A
// Passing the base URL as expected by A2A client
export const remoteA2AAgent = defineA2ASessionFlow(ai, {
  name: 'remoteA2AAgent',
  description: 'Consumes a remote A2A agent',
  agentUrl: 'http://localhost:8080',
});

// 2. Test Flow to run it
export const runClientTest = ai.defineFlow(
  {
    name: 'runClientTest',
    inputSchema: z.string().default('Hello from client!'),
    outputSchema: z.any(),
  },
  async (text) => {
    const res = await remoteA2AAgent.run(
      {
        messages: [{ role: 'user' as const, content: [{ text }] }],
      },
      { init: {} }
    );

    console.log(
      'Client received response:',
      res.result.message?.content?.[0]?.text
    );
    return res.result;
  }
);
