import { generate } from '@genkit-ai/ai/generate';
import { initializeGenkit } from '@genkit-ai/common/config';
import { flow, run, runFlow } from '@genkit-ai/flow';
import { geminiPro } from '@genkit-ai/plugin-vertex-ai';
import * as z from 'zod';
import config from './genkit.conf';
import { gpt35Turbo } from '@genkit-ai/plugin-openai';

initializeGenkit(config);

function promptSimple({ customerName }: { customerName: string }) {
  return `
  You're a barista at a high end coffee shop.  
  The customers name is ${customerName}.  
  
  Write a greeting for the customer in 15 words or less, and recommend a drink.
  `;
}

const SimpleOrderHistorySchema = z.object({
  customerName: z.string(),
  currentTime: z.string(),
  previousOrder: z.string(),
});

export type orderHistoryType = z.infer<typeof SimpleOrderHistorySchema>;

const MenuItemSchema = z.object({
  name: z.string(),
  id: z.string(),
  price: z.number(),
  description: z.string().optional(),
  specialOfTheDay: z.boolean(),
});

const PreviousOrderSchema = z.object({
  orderDate: z.string().datetime(),
  menuItem: MenuItemSchema,
});

const ComplexCoffeeShopSchema = z.object({
  customerName: z.string(),
  customerId: z.string().optional(),
  currentTime: z.string().datetime(),
  previousOrders: z.array(PreviousOrderSchema),
  currentMenuItems: z.array(MenuItemSchema),
});

export type complexOrderHistoryType = z.infer<typeof ComplexCoffeeShopSchema>;

function promptWithSimpleHistory({ previousOrder }: { previousOrder: string }) {
  return `
You're a barista at a high end coffee shop.

Write a greeting for this customer in 20 words or less and recommend a drink.

In you're response, account for the fact that the current time is {current_time},
and the customer's previous order was:

  Order: ${previousOrder}
`;
}

function promptForJudgement({
  llmRequest,
  llmResponse,
}: {
  llmRequest: string;
  llmResponse: string;
}) {
  return `
You're a nitpicky and detailed oriented judge of LLM responses.  
Your job is to score an LLM response between 0 and 5,
where 0 is a very poor response and 5 is great.

Carefully consider each aspect of the request that went 
to the LLM and how it responsed and then respond ONLY with a number between 0 and 5

What the LLM was asked:
========================
${llmRequest}
========================

What the LLM responded with:
========================
${llmResponse}
========================


Your score:
`;
}

function makeComplexPrompt(orderHistory: complexOrderHistoryType) {
  const previousOrdersString = orderHistory.previousOrders
    .map((item) => {
      return `${item.orderDate} | ${item.menuItem.name} | ${item.menuItem.price}`;
    })
    .join('\n');

  const specialsOfTheDay = orderHistory.currentMenuItems
    .filter((item) => {
      return item.specialOfTheDay;
    })
    ?.map((item) => {
      return `${item.name} | ${item.description} | ${item.price}`;
    })
    .join('\n');

  return `
  You're a professional, expert barista at a coffeeshop, recommend a drink for this customer
   in 15 words or less, here's the context you need: 
  
   the customer name is ${orderHistory.customerName}
   the current time is ${orderHistory.currentTime}
   
   
   they've had previous orders:
  ============= PREVIOUS ORDERS ==============
  ${previousOrdersString}
  ============================================

  Today's specials are:
  ============= SPECIALS =====================
  ${specialsOfTheDay}
  ============================================

  Only suggest the special of the day if it's similar to the other drinks they've
  ordered in the past, or if they don't have any previous order history
  `;
}

export const basicCoffeeRecommender = flow(
  { name: 'coffeeFlow', input: z.string(), output: z.string() },
  async (name) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: geminiPro,
        prompt: promptSimple({
          customerName: name,
        }),
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
    input: SimpleOrderHistorySchema,
    output: z.string(),
  },
  async (query) => {
    const llmResponse = await generate({
      model: geminiPro,
      prompt: promptWithSimpleHistory(query),
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
    const initialPrompt = promptSimple({ customerName });
    const llmResponse = await generate({
      model: gpt35Turbo,
      prompt: initialPrompt,
      config: {
        temperature: 1,
      },
    });

    console.log(`Response: ${llmResponse.text()}`);
    console.log(`Request: ${initialPrompt}`);

    const judgeResponse = await generate({
      model: gpt35Turbo,
      prompt: promptForJudgement({
        llmRequest: initialPrompt,
        llmResponse: llmResponse.text(),
      }),
      config: {
        temperature: 1,
      },
    });

    return judgeResponse.text();
  }
);

export const complexOrderHistoryFlow = flow(
  {
    name: 'complexOrderHistoryFlow',
    input: ComplexCoffeeShopSchema,
    output: z.string(),
  },
  async (complexOrderHistory) => {
    const prompt = makeComplexPrompt(complexOrderHistory);

    const response = await generate({
      model: geminiPro,
      prompt: prompt,
    });

    return response.text();
  }
);

/* 
*  Invokes each flow with some static inputs to validate they're all working
   as expected.  Test with
*  genkit flow:run testAllFlows
*/
export const testAllFlows = flow(
  {
    name: 'testAllFlows',
    input: z.void(),
    output: z.void(),
  },
  async () => {
    // Test the most simple case
    const basicCoffeeOperation = await runFlow(basicCoffeeRecommender, 'Sam');
    console.log('Basic Coffee Recomender', basicCoffeeOperation);

    // Test with simple structured input
    const historyCoffeeOperation = await runFlow(historyCoffeeRecommender, {
      customerName: 'Max',
      currentTime: '12:30AM',
      previousOrder: 'Maple Cortado',
    });
    console.log('History Coffee recommendation', historyCoffeeOperation);

    // Use an LLM to judge the response
    const judgedCoffeeRecomendation = await runFlow(judgeResponseFlow, 'Sam');
    console.log('Judgement: ', judgedCoffeeRecomendation);

    // Pass in a complex object
    const complexOrderReccomendation = await runFlow(complexOrderHistoryFlow, {
      customerName: 'sam',
      currentTime: '2024-02-20T00:00:00Z',
      previousOrders: [
        {
          orderDate: '2024-02-05T00:00:00Z',
          menuItem: {
            name: 'Earl Grey tea, hot',
            id: '13431',
            price: 4.22,
            specialOfTheDay: true,
            description: 'Delcicious Earl Grey tea from England',
          },
        },
      ],
      currentMenuItems: [
        {
          name: 'Americano',
          id: '214',
          price: 3.5,
          specialOfTheDay: true,
          description: 'A rich dark pull from our new Aeropress',
        },
      ],
      customerId: undefined,
    });
    console.log('Complex order history response', complexOrderReccomendation);
  }
);
