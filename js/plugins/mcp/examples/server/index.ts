import { genkit, z } from "genkit";
import { mcpServer } from "@genkit-ai/mcp";

const ai = genkit({});

ai.defineTool(
  {
    name: "add",
    description: "add two numbers together",
    inputSchema: z.object({ a: z.number(), b: z.number() }),
    outputSchema: z.number(),
  },
  async ({ a, b }) => {
    return a + b;
  }
);

ai.definePrompt(
  {
    name: "happy",
    description: "everybody together now",
    input: {
      schema: z.object({ action: z.string().optional() }),
      default: { action: "clap your hands" },
    },
  },
  `If you're happy and you know it, {{action}}.`
);

mcpServer(ai, { name: "example_server", version: "0.0.1" }).start();
