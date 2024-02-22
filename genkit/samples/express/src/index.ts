import { generate } from '@google-genkit/ai/generate';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, run, runFlow } from '@google-genkit/flow';
import express from 'express';
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

app.get(
  '/jokeWithFlow',
  async (req: express.Request, res: express.Response) => {
    const subject = req.query['subject']?.toString();
    if (!subject) {
      res.status(400).send('provide subject query param');
      return;
    }
    const operation = await runFlow(jokeFlow, subject);
    res.send(operation.result?.response);
  }
);

app.get('/jokeStream', async (req: express.Request, res: express.Response) => {
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
