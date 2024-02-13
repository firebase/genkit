"use strict";

const { getProjectId } = require("@google-genkit/common");
const { configureGenkit } = require("@google-genkit/common/config");
const { configureVertexAiTextModel } = require("@google-genkit/providers/llms");
const { googleAI } = require("@google-genkit/providers/models");
const { firestoreStores } = require("@google-genkit/providers/stores");

configureGenkit({
  plugins: [
    firestoreStores({projectId: getProjectId()}),
    googleAI(),
  ],
  flowstore: "firestoreStores",
  tracestore: "firestoreStores",
  enableTracingAndMetrics: true,
  logLevel: "info",
})
