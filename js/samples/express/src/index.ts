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

import { generate } from '@genkit-ai/ai/generate';
import { initializeGenkit } from '@genkit-ai/common/config';
import { flow, run, runFlow } from '@genkit-ai/flow';
import express, { Request, Response } from 'express';
import * as z from 'zod';
import config from './genkit.conf';

initializeGenkit(config);

export const jokeFlow = flow(
  { name: 'jokeFlow', input: z.string(), output: z.string() },
  async (subject) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        prompt: `Tell me a joke about ${subject}`,
        model: 'ollama/llama2',
        config: {
          temperature: 1,
        },
        streamingCallback: (c) => console.log(c.content[0].text),
      });

      return llmResponse.text();
    });
  }
);

const app = express();
const port = process.env.PORT || 5000;

app.get('/jokeWithFlow', async (req: Request, res: Response) => {
  const subject = req.query['subject']?.toString();
  if (!subject) {
    res.status(400).send('provide subject query param');
    return;
  }
  res.send(await runFlow(jokeFlow, subject));
});

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
  await generate({
    prompt: `Tell me a joke about ${subject}`,
    model: 'ollama/llama2',
    config: {
      temperature: 1,
    },
    streamingCallback: (c) => {
      console.log(c.content[0].text);
      res.write(c.content[0].text);
    },
  });

  res.end();
});

app.listen(port, () => {
  console.log(`Example app listening on port ${port}`);
});
