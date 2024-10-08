import { Genkit } from '../src/genkit';

export function defineEchoModel(ai: Genkit) {
  ai.defineModel(
    {
      name: 'echoModel',
    },
    async (request, streamingCallback) => {
      if (streamingCallback) {
        await runAsync(() => {
          streamingCallback({
            content: [
              {
                text: '3',
              },
            ],
          });
        });
        await runAsync(() => {
          streamingCallback({
            content: [
              {
                text: '2',
              },
            ],
          });
        });
        await runAsync(() => {
          streamingCallback({
            content: [
              {
                text: '1',
              },
            ],
          });
        });
      }
      return await runAsync(() => ({
        message: {
          role: 'model',
          content: [
            {
              text:
                'Echo: ' +
                request.messages
                  .map((m) => m.content.map((c) => c.text).join())
                  .join(),
            },
            {
              text: '; config: ' + JSON.stringify(request.config),
            },
          ],
        },
        finishReason: 'stop',
      }));
    }
  );
}

async function runAsync<O>(fn: () => O): Promise<O> {
  return Promise.resolve(fn());
}
