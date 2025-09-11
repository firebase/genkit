import { openAI } from '@genkit-ai/compat-oai/openai';

(async () => {
  const oai = openAI({ apiKey: '...' });
  const gpt4o = await oai.model('gpt-4o');
  const response = await gpt4o({
    messages: [
      {
        role: 'user',
        content: [{ text: 'what is a gablorken of 4!' }],
      },
    ],
    tools: [
      {
        name: 'gablorken',
        description: 'calculates a gablorken',
        inputSchema: {
          type: 'object',
          properties: {
            value: {
              type: 'number',
              description: 'the value to calculate gablorken for',
            },
          },
        },
      },
    ],
  });

  console.log(JSON.stringify(response.message, undefined, 2));
})();
