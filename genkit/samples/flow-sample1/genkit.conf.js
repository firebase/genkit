"use strict";

const { getProjectId } = require("@google-genkit/common");
const { configureGenkit } = require("@google-genkit/common/config");
const { firestoreStores } = require("@google-genkit/providers/stores");

configureGenkit({
  plugins: [
    firestoreStores({projectId: getProjectId()}),
  ],
  flowstore: "firestoreStores",
  tracestore: "firestoreStores",
  enableTracingAndMetrics: true,
  logLevel: "info",
})
