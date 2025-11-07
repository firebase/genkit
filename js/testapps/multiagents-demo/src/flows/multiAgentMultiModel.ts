import { ai } from "../config/genkit";
import { z } from "genkit";
import { triageAgent } from "../agents";

export const flow = ai.defineFlow({
    name: 'multiAgentMultiModel',
    inputSchema: z.object({
        userInput: z.string(),
    }),
    outputSchema: z.string(),
}, async (input) => {
    const chat = ai.chat(triageAgent);
    const response = await chat.send(input.userInput);
    return response.output?.text;
});