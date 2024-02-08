
import { getProjectId } from "@google-genkit/common";
import { setLogLevel } from "@google-genkit/common/logging";
import {
  enableTracingAndMetrics,
  useFirestoreTraceStore
} from "@google-genkit/common/tracing";
import { flow, run, runFlow, useFirestoreStateStore } from "@google-genkit/flow";
import * as z from "zod";

setLogLevel("debug")

useFirestoreStateStore({ projectId: getProjectId() });
useFirestoreTraceStore({ projectId: getProjectId() });

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