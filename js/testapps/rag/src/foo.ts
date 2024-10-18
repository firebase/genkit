import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit } from 'genkit';
import readline from 'node:readline';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

const refundAgent = ai.definePrompt(
  {
    name: 'refundAgent',
    config: { temperature: 1 },
    description: 'Refunds Agent',
  },
  '{{role "system"}} Help the user with a refund. If the reason is that it was too expensive, offer the user a refund code. If they insist, then process the refund.'
);

const salesAgent = ai.definePrompt(
  {
    name: 'salesAgent',
    config: { temperature: 1 },
    description: 'Sales Agent',
    tools: [refundAgent],
  },
  '{{role "system"}} Be super enthusiastic about selling bees.'
);

const triageAgent = ai.definePrompt(
  {
    name: 'triageAgent',
    config: { temperature: 1 },
    description: 'triage Agent',
    tools: [salesAgent, refundAgent],
  },
  '{{role "system"}} greet the person, ask them about what they need and if appropriate transfer an agents that can better handle the query'
);

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

(async () => {
  const session = ai.chat({
    prompt: triageAgent,
  });
  while (true) {
    await new Promise((resolve) => {
      rl.question(`Say: `, async (input) => {
        const { text } = await session.send(input);
        console.log(text);
        resolve(null);
      });
    });
  }
})();