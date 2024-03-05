import { getProjectId, getLocation } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { openAI } from '@google-genkit/plugin-openai';
import { googleGenAI } from '@google-genkit/plugin-google-genai';
import { vertexAI } from '@google-genkit/plugin-vertex-ai';
import { firebase } from '@google-genkit/providers/firebase';
import { gcp } from '@google-genkit/plugin-gcp';
import { AlwaysOnSampler } from '@opentelemetry/core';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    googleGenAI(),
    openAI(),
    vertexAI({ projectId: getProjectId(), location: getLocation() }),
    gcp({
      projectId: getProjectId(),
      // These are configured for demonstration purposes. Sensible defaults are
      // in place in the event that telemetryConfig is absent.
      telemetryConfig: {
        sampler: new AlwaysOnSampler(),
        autoInstrumentation: true,
        autoInstrumentationConfig: {
          '@opentelemetry/instrumentation-fs': { enabled: false },
          '@opentelemetry/instrumentation-dns': { enabled: false },
          '@opentelemetry/instrumentation-net': { enabled: false },
        },
      },
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
  telemetry: {
    instrumentation: 'gcp',
  },
});
