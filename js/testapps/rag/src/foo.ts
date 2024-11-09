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
    description: 'Refunds Agent can help with refund inquiries',
  },
  '{{role "system"}} Help the user with a refund.'
);

const salesAgent = ai.definePrompt(
  {
    name: 'salesAgent',
    config: { temperature: 1 },
    description: 'Sales Agent can help with sales or product inquiries',
    tools: [refundAgent],
  },
  '{{role "system"}} Be super enthusiastic about selling stuff we offer'
);

const triageAgent = ai.definePrompt(
  {
    name: 'triageAgent',
    config: { temperature: 1 },
    description: 'triage Agent',
    tools: [salesAgent, refundAgent],
  },
  '{{role "system"}} greet the person, ask them about what they need and if appropriate transfer to an agents that can better handle the query'
);

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

(async () => {
  const chat = ai.chat({
    preamble: triageAgent,
  });
  while (true) {
    await new Promise((resolve, reject) => {
      rl.question(`Say: `, async (input) => {
        try {
          const { stream } = await chat.sendStream(input);
          for await (const chunk of stream) {
            process.stdout.write(chunk.text);
          }
          resolve(null);
        } catch (e) {
          console.log('e', e);
        }
      });
    });
  }
})();
