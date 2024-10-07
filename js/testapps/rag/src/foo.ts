import { vertexAI } from '@genkit-ai/vertexai';
import { genkit, z } from 'genkit';
import { modelRef } from 'genkit/model';

const ai = genkit({
  plugins: [vertexAI({ location: 'us-central1' })],
  model: modelRef({
    name: 'vertexai/gemini-1.5-flash',
    config: {
      temperature: 1,
    },
  }),
});

const Weapon = z.object({
  name: z.string().describe('name of the weapon'),
  description: z.string().describe('description on the weapon, one paragraph'),
  power: z.number().describe('power level, between 1 and 10'),
});

const Character = z.object({
  name: z.string().describe('name of the character'),
  background: z.string().describe('background story, one paragraph'),
  weapon: Weapon,
});

(async () => {
  let response;

  response = await ai.generate('tell me joke?');
  console.log(response.text());

  response = await ai.generate({
    prompt: 'create a RPG character, archer',
    output: {
      format: 'json',
      schema: Character,
    },
  });

  // text chat
  let chatbotSession = ai.createSession();
  response = await chatbotSession.send('hi my name is John');
  console.log(response.text());
  response = await chatbotSession.send('who am I?');
  console.log(response.text()); // { answer: '...John...' }


  // json chat 
  chatbotSession = ai.createSession({
    output: {
      schema: z.object({
        answer: z.string(),
      }),
      format: 'json',
    },
  });
  response = await chatbotSession.send('hi my name is John');
  console.log(response.output());
  response = await chatbotSession.send('who am I?');
  console.log(response.output()); // { answer: '...John...' }

  // Agent
  const agent = ai.defineEnvironment({
    name: 'agent',
    stateSchema: z.object({ name: z.string(), done: z.boolean() }),
  });

  const agentFlow = agent.defineFlow({ name: 'agentFlow' }, async () => {
    const response = await agent.currentSession.send(
      `hi, my name is ${agent.currentSession.state.name}`
    );
    await agent.currentSession.updateState({
      ...agent.currentSession.state,
      done: true,
    });
    return response.text();
  });

  const session = agent.createSession({
    state: {
      name: 'Bob',
      done: false,
    },
  });

  console.log(session.state); // { name: 'Bob', done: false }
  console.log(await session.runFlow(agentFlow, undefined));
  console.log(session.state); // { name: 'Bob', done: true }
  response = await session.send('What is my name?');
  console.log(response.text()); // { answer: '...Bob...' }
  console.log(JSON.stringify(session.messages, undefined, '  '));
})();
