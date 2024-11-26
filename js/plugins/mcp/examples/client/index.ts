import { genkit } from "genkit";
import { gemini15Pro, googleAI } from "@genkit-ai/googleai";
import { mcpClient } from "@genkit-ai/mcp";
import { logger } from "genkit/logging";

logger.setLogLevel("debug");

const everythingClient = mcpClient({
  name: "everything",
  version: "1.0.0",
  serverProcess: {
    command: "npx",
    args: ["@modelcontextprotocol/server-everything"],
  },
});

const ai = genkit({
  plugins: [googleAI(), everythingClient],
  model: gemini15Pro,
});

ai.registry.initializeAllPlugins();
