import * as z from "zod";
import { flow, runFlow, useFirestoreStateStore, run } from "@google-genkit/flow";
import { configureVertexAiTextModel } from "@google-genkit/providers/llms";
import { promptTemplate, loadPrompt } from "@google-genkit/ai";
import { generateText } from "@google-genkit/ai/text";
import { getProjectId } from "@google-genkit/common";
import { setLogLevel } from "@google-genkit/common/logging";
import {
  enableTracingAndMetrics,
  flushTracing,
  useFirestoreTraceStore,
} from "@google-genkit/common/tracing";

setLogLevel("debug");

useFirestoreStateStore({ projectId: getProjectId() });
useFirestoreTraceStore({ projectId: getProjectId() });

enableTracingAndMetrics();

const gemini = configureVertexAiTextModel({ modelName: "gemini-pro" });

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
