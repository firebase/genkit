import { loadPrompt, promptTemplate } from "@google-genkit/ai";
import { generateText } from "@google-genkit/ai/text";
import { initializeGenkit } from "@google-genkit/common/config";
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
      const llmResponse = await generateText({ prompt });

      return llmResponse.completion;
    });
  }
);

async function main() {
  const operation = await runFlow(jokeFlow, "banana");
  console.log("Operation", operation);
}

main();
