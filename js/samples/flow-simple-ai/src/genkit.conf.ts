import { getLocation, getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { firebase } from '@google-genkit/plugin-firebase';
import { gcp } from '@google-genkit/plugin-gcp';
import { googleGenAI } from '@google-genkit/plugin-google-genai';
import { openAI } from '@google-genkit/plugin-openai';
import { vertexAI } from '@google-genkit/plugin-vertex-ai';
import { AlwaysOnSampler } from '@opentelemetry/sdk-trace-base';

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
        metricExportIntervalMillis: 5_000,
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
