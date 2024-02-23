import { generate } from '@google-genkit/ai/generate';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, run, runFlow } from '@google-genkit/flow';
import { geminiPro } from '@google-genkit/providers/google-ai';
import * as z from 'zod';
import config from './genkit.conf';
import { gpt35Turbo } from '@google-genkit/providers/openai';
import { promptTemplate } from '@google-genkit/ai';

initializeGenkit(config);

const promptSimple = `
You're a barista at a high end coffee shop.  
The customers name is {customerName}.  

Write a greeting for the customer in 15 words or less, and recommend a drink.
`;

const orderHistorySchema = z.object({
  customerName: z.string(),
  currentTime: z.string(),
  previousOrder: z.string(),
});

const promptWithHistory = `
You're a barista at a high end coffee shop.

Write a greeting for this customer in 20 words or less and recommend a drink.

In you're response, account for the fact that the current time is {current_time},
and the customer's previous order was:

  Order: {previousOrder}
`;

const promptForJudgement = `
You're a nitpicky and detailed oriented judge of LLM responses.  
Your job is to score an LLM response between 0 and 5,
where 0 is a very poor response and 5 is great.

Carefully consider each aspect of the request that went 
to the LLM and how it responsed and then respond ONLY with a number between 0 and 5

What the LLM was asked:
========================
{llmRequest}
========================

What the LLM responded with:
========================
{llmResponse}
========================


Your score:
`;

export const basicCoffeeRecommender = flow(
  { name: 'coffeeFlow', input: z.string(), output: z.string() },
  async (name) => {
    return await run('call-llm', async () => {
      const simpleTemplate = await promptTemplate({
        template: promptSimple,
        variables: {
          customerName: name,
        },
      });

      const llmResponse = await generate({
        model: geminiPro,
        prompt: simpleTemplate.prompt,
        config: {
          temperature: 1,
        },
      });

      return llmResponse.text();
    });
  }
);

export const historyCoffeeRecommender = flow(
  {
    name: 'Recommender with history',
    input: orderHistorySchema,
    output: z.string(),
  },
  async (query) => {
    const templateWithHistory = await promptTemplate({
      template: promptWithHistory,
      variables: query,
    });

    const llmResponse = await generate({
      model: geminiPro,
      prompt: templateWithHistory.prompt,
      config: {
        temperature: 1,
      },
    });
    return llmResponse.text();
  }
);

// Run a simple flow and judge the response
export const judgeResponseFlow = flow(
  {
    name: 'judgeResponseFlow',
    input: z.string(),
    output: z.string(),
  },
  async (customerName) => {
    const simpleTemplate = await promptTemplate({
      template: promptSimple,
      variables: {
        customerName: customerName,
      },
    });

    const llmResponse = await generate({
      model: gpt35Turbo,
      prompt: simpleTemplate.prompt,
      config: {
        temperature: 1,
      },
    });

    const judgeTemplate = await promptTemplate({
      template: promptForJudgement,
      variables: {
        llmRequest: simpleTemplate.prompt,
        llmResponse: llmResponse.text(),
      },
    });

    console.log(`Response: ${llmResponse.text()}`);
    console.log(`Request: ${simpleTemplate.prompt}`);

    const judgeResponse = await generate({
      model: gpt35Turbo,
      prompt: judgeTemplate.prompt,
      config: {
        temperature: 1,
      },
    });

    return judgeResponse.text();
  }
);

async function main() {
  // Call using a basic input
  const basicCoffeeOperation = await runFlow(basicCoffeeRecommender, 'Sam');
  console.log('Basic Coffee Recomender', basicCoffeeOperation);

  // Pass structured input
  const historyCoffeeOperation = await runFlow(historyCoffeeRecommender, {
    customerName: 'Max',
    currentTime: '12:30AM',
    previousOrder: 'Maple Cortado',
  });
  console.log('History Coffee recommendation', historyCoffeeOperation);

  // Use an LLM to judge the response
  const judgedCoffeeRecomendation = await runFlow(judgeResponseFlow, 'Sam');
  console.log('Judgement: ', judgedCoffeeRecomendation);
}

main().catch(console.error);
