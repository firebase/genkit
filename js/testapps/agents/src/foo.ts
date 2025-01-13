import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit } from 'genkit';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

const fetchRecentOrders = ai.defineTool(
  {
    name: 'fetchRecentOrders',
    description: 'can be used to fetch recent orders',
  },
  async () => {
    return [
      {
        orderId: 123,
        products: [
          {
            id: '456',
            name: 'Asus Laptop',
            price: 567.43,
          },
        ],
        shippingAdddress: {
          city: 'New York',
        },
      },
    ];
  }
);

const fetchShippingSchedules = ai.defineTool(
  {
    name: 'fetchShippingSchedules',
    description: 'can be used to fetch shipping schedules',
  },
  async () => {
    return {
      'New York': '3 business days',
      'San Francisco': '2 business days',
      Toronto: '5 business days',
    };
  }
);
(async () => {
  const response = await ai.generate({
    prompt: 'when will I get my order',
    tools: [fetchRecentOrders, fetchShippingSchedules],
  });
  console.log(response.text);
})();
