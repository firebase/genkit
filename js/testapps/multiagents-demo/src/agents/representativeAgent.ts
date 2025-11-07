import { ai } from "../config/genkit";
import { getStoreInfoTool } from "../tools";

// Simple agent for providing store information
export const agent = ai.definePrompt({
    name: 'representativeAgent',
    model: "googleai/gemini-2.0-flash",
    description:
      'Representative Agent can provide store info',
    tools: [getStoreInfoTool],
    system: `You are a customer service representative for TechStore Computer Shop.
      Help customers provide store information.`,
  });   