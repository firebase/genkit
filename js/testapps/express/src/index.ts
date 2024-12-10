/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { AuthPolicy, RequestWithAuth, handler } from '@genkit-ai/express';
import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { vertexAI } from '@genkit-ai/vertexai';
import express, {
  ErrorRequestHandler,
  Handler,
  Request,
  Response,
} from 'express';
import { genkit, run, z } from 'genkit';
import { logger } from 'genkit/logging';
import { ollama } from 'genkitx-ollama';

logger.setLogLevel('debug');

const ai = genkit({
  plugins: [
    googleAI(),
    vertexAI(),
    ollama({
      models: [
        { name: 'llama2', type: 'generate' },
        { name: 'gemma', type: 'chat' },
      ],
      serverAddress: 'http://127.0.0.1:11434', // default local address
    }),
  ],
});

export const jokeFlow = ai.defineFlow(
  { name: 'jokeFlow', inputSchema: z.string(), outputSchema: z.string() },
  async (subject, streamingCallback) => {
    return await run('call-llm', async () => {
      const llmResponse = await ai.generate({
        prompt: `tell me long joke about ${subject}`,
        model: gemini15Flash,
        config: {
          temperature: 1,
        },
        streamingCallback,
      });

      return llmResponse.text;
    });
  }
);

const auth: Handler = (req, resp, next) => {
  const token = req.header('authorization');
  // pretend we check auth token
  (req as RequestWithAuth).auth = {
    username: token === 'open sesame' ? 'Ali Baba' : '40 thieves',
  };
  next();
};

const app = express();
app.use(express.json());

const authPolicies: Record<string, AuthPolicy> = {
  jokeFlow: ({ auth }) => {
    if (auth.username != 'Ali Baba') {
      throw new Error('unauthorized: ' + JSON.stringify(auth));
    }
  },
};

// curl http://localhost:5000/jokeFlow?stream=true -d '{"data": "banana"}' -H "content-type: application/json" -H "authorization: open sesame"
ai.flows.forEach((f) => {
  app.post(
    `/${f.name}`,
    auth,
    handler(f, { authPolicy: authPolicies[f.name] })
  );
});

// curl http://localhost:5000/jokeHandler?stream=true -d '{"data": "banana"}' -H "content-type: application/json"
app.post('/jokeHandler', handler(jokeFlow));

// curl http://localhost:5000/jokeWithFlow?subject=banana
app.get('/jokeWithFlow', async (req: Request, res: Response) => {
  const subject = req.query['subject']?.toString();
  if (!subject) {
    res.status(400).send('provide subject query param');
    return;
  }
  res.send(await jokeFlow(subject));
});

// curl http://localhost:5000/jokeStream?subject=banana
app.get('/jokeStream', async (req: Request, res: Response) => {
  const subject = req.query['subject']?.toString();
  if (!subject) {
    res.status(400).send('provide subject query param');
    return;
  }

  res.writeHead(200, {
    'Content-Type': 'text/plain',
    'Transfer-Encoding': 'chunked',
  });
  await ai.generate({
    prompt: `Tell me a long joke about ${subject}`,
    model: gemini15Flash,
    config: {
      temperature: 1,
    },
    streamingCallback: (c) => {
      res.write(c.content[0].text);
    },
  });

  res.end();
});

const errorHandler: ErrorRequestHandler = (error, request, response, next) => {
  if (error instanceof Error) {
    console.log(error.stack);
  }
  return response.status(500).send(error);
};
app.use(errorHandler);

const port = process.env.PORT || 5000;
app.listen(port, () => {
  console.log(`Example app listening on port ${port}`);
});
