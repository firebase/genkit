import { ai } from "../config/genkit";
import { processPaymentTool } from "../tools";

// Simple agent for processing payments
export const paymentAgent = ai.definePrompt({
    name: 'paymentAgent',
    model: "googleai/gemini-2.5-flash-lite",
    description:
      'Payment Agent can help process payments',
    tools: [processPaymentTool],
    system: `You are a payment agent for TechStore Computer Shop.
      Help customers process payments.
      Always confirm payment details before processing and provide clear transaction information.`,
  });