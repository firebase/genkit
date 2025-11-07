import { ai } from '../config/genkit';
import { agent as catalogAgent } from './catalogAgent';
import { agent as paymentAgent } from './paymentAgent';
import { agent as representativeAgent } from './representativeAgent';

// The triage agent routes customers to the appropriate specialist
export const agent = ai.definePrompt({
  name: 'triageAgent',
  description: 'Triage Agent',
  model: "googleai/gemini-2.5-flash",
  tools: [catalogAgent, paymentAgent, representativeAgent],
  system: `You are an AI customer service agent for TechStore Computer Shop.
    Greet the user and ask them how you can help. Route them to the appropriate specialist agent:
    - Use catalogAgent for browsing products, searching items, or getting product information
    - Use paymentAgent for payment processing
    - Use representativeAgent for providing store information
    If you cannot help the customer with the available tools, politely explain so.`,
});
