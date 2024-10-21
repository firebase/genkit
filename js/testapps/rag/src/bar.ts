import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit, z } from 'genkit';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

const agents = ai.defineEnvironment({
  name: 'agentEnv',
  stateSchema: z.object({
    foo: z.string().optional(),
  }),
});

const delegate = ai.defineFlow({
  name: 'delegate',
  description: 'useful to delegate',
}, async () => {
  console.log(agents.currentSession.state)
});

(async () => {
  const session = agents.createSession({
    initialState: {
      foo: 'bar'
    }
  });

  await session.chat().send({
    prompt: 'call the delegate tool',
    tools: [delegate],
  })
})();