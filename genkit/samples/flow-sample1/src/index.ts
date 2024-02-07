
import * as z from "zod";
import { flow, useDevStateStore, run, runFlow } from "@google-genkit/flow";
import { setLogLevel } from "@google-genkit/common/logging";
import {
  enableTracingAndMetrics,
  useDevTraceStore,
} from "@google-genkit/common/tracing";

setLogLevel("debug")

useDevStateStore();
useDevTraceStore();

enableTracingAndMetrics();

export const jokeFlow = flow(
  { name: "jokeFlow", input: z.string(), output: z.string(), local: true },
  async (subject) => {
    const foo = await run("call-llm", async () => {
      return `subject: ${subject}`;
    });
    return await run("call-llm", async () => {
      return `foo: ${foo}`;
    });
  }
);

async function main() {
  const op = await runFlow(jokeFlow, "subj")
  console.log(op)
}

main()