"use strict";

const { getProjectId } = require("@google-genkit/common");
const { genkitConfig } = require("@google-genkit/common/config");
const { FirestoreTraceStore } = require("@google-genkit/common/tracing");
const { FirestoreStateStore } = require("@google-genkit/flow");
const { configureVertexAiTextModel } = require("@google-genkit/providers/llms");

exports.default = genkitConfig({
  flowstore: new FirestoreStateStore({ projectId: getProjectId() }),
  tracestore: new FirestoreTraceStore({ projectId: getProjectId() }),
  models: [
    configureVertexAiTextModel({ modelName: "gemini-pro" })
  ],
  enableTracingAndMetrics: true,
  logLevel: "info",
})
