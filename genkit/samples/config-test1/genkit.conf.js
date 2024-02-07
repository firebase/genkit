"use strict";

const { getProjectId } = require("@google-genkit/common");
const { genkitConfig } = require("@google-genkit/common/config");
const { setLogLevel } = require("@google-genkit/common/logging");
const { configureVertexAiTextModel } = require("@google-genkit/providers/llms");
const { firestoreStores } = require("@google-genkit/providers/stores");

setLogLevel("debug")

exports.default = genkitConfig({
  plugins: [firestoreStores({projectId: getProjectId()})],
  flowstore: "firestoreStores",
  tracestore: "firestoreStores",
  models: [
    configureVertexAiTextModel({ modelName: "gemini-pro" })
  ],
  enableTracingAndMetrics: true,
  logLevel: "info",
})
