import { loadPrompt, promptTemplate } from "@google-genkit/ai";
import { generate } from "@google-genkit/ai/generate";
import { initializeGenkit } from "@google-genkit/common/config";
import { geminiPro } from "@google-genkit/providers/models";
import { flow, run, runFlow } from "@google-genkit/flow";
import * as z from "zod";

initializeGenkit();

export const jokeFlow = flow(
  { name: "jokeFlow", input: z.string(), output: z.string(), local: true },
  async (subject) => {
    const prompt = await promptTemplate({
      template: loadPrompt(__dirname + "/../prompts/TellJoke.prompt"),
      variables: { subject },
    });

    return await run("call-llm", async () => {
      const llmResponse = await generate({ prompt: "Tell me a joke", model: geminiPro});

      return llmResponse.text();
    });
  }
);

async function main() {
  const operation = await runFlow(jokeFlow, "banana");
  console.log("Operation", operation);
}

main();
