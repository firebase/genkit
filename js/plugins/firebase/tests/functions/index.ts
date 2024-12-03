import { enableFirebaseTelemetry } from '@genkit-ai/firebase';
import { noAuth, onFlow } from '@genkit-ai/firebase/functions';
import { genkit, z } from 'genkit';

process.env.GENKIT_ENV = 'dev';

const ai = genkit({});
enableFirebaseTelemetry({});

export const simpleFlow = onFlow(
  ai,
  {
    name: 'simpleFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
    httpsOptions: {
      cors: '*',
    },
    authPolicy: noAuth(),
  },
  async (subject) => {
    return 'hello world!';
  }
);
