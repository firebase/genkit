import { AGENT_CARD_PATH, AgentCard } from '@a2a-js/sdk';
import { DefaultRequestHandler, InMemoryTaskStore } from '@a2a-js/sdk/server';
import {
  UserBuilder,
  agentCardHandler,
  jsonRpcHandler,
  restHandler,
} from '@a2a-js/sdk/server/express';
import { SessionFlowAgentExecutor } from '@genkit-ai/a2a';
import express from 'express';
import { ai } from './genkit.js';

// 1. Define Genkit Session Flow
export const myFlow = ai.defineSessionFlow(
  { name: 'myFlow' },
  async (sess, { sendChunk }) => {
    await sess.run(async (input) => {
      const text =
        input.messages?.[input.messages.length - 1]?.content[0]?.text || '';

      sendChunk({
        modelChunk: {
          role: 'model',
          content: [{ text: `Server received: ${text}` }],
        },
      });
    });

    const msgs = sess.session.getMessages();
    return {
      message: msgs[msgs.length - 1],
    };
  }
);

// 2. Expose as A2A Agent
const card: AgentCard = {
  name: 'Genkit Test Agent',
  description: 'Genkit Session Flow exposed via A2A',
  protocolVersion: '0.3.0',
  version: '0.1.0',
  url: 'http://localhost:8080/a2a/jsonrpc',
  skills: [
    {
      id: 'chat',
      name: 'Chat',
      description: 'Chat with agent',
      tags: ['chat'],
    },
  ],
  capabilities: {
    pushNotifications: false,
  },
  defaultInputModes: ['text'],
  defaultOutputModes: ['text'],
};

const executor = new SessionFlowAgentExecutor(myFlow);
const requestHandler = new DefaultRequestHandler(
  card,
  new InMemoryTaskStore(),
  executor
);

const app = express();
app.use(express.json()); // Ensure body parsing
app.use(
  `/${AGENT_CARD_PATH}`,
  agentCardHandler({ agentCardProvider: requestHandler })
);
app.use(
  '/a2a/jsonrpc',
  jsonRpcHandler({ requestHandler, userBuilder: UserBuilder.noAuthentication })
);
app.use(
  '/a2a/rest',
  restHandler({ requestHandler, userBuilder: UserBuilder.noAuthentication })
);

export function startServer() {
  return app.listen(8080, () =>
    console.log('🚀 A2A Server started on http://localhost:8080')
  );
}
