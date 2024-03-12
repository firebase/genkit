import { getProjectId } from '@genkit-ai/common';
import { configureGenkit } from '@genkit-ai/common/config';
import { openAI } from '@genkit-ai/plugin-openai';
import { googleGenAI } from '@genkit-ai/plugin-google-genai';
import { ollama } from '@genkit-ai/plugin-ollama';
import { firebase } from '@genkit-ai/plugin-firebase';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    googleGenAI(),
    openAI(),
    ollama({
      models: [{ name: 'llama2' }],
      serverAddress: 'http://127.0.0.1:11434', // default local port
      pullModel: false,
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
