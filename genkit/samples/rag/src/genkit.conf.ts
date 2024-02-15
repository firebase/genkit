import { getProjectId } from "@google-genkit/common";
import { configureGenkit } from "@google-genkit/common/config";
import { googleAI, openAI } from "@google-genkit/providers/models";
import { firestoreStores } from "@google-genkit/providers/stores";

export default configureGenkit({
  plugins: [
    firestoreStores({projectId: getProjectId()}),
    googleAI(),
  ],
  flowStateStore: "firestoreStores",
  traceStore: "firestoreStores",
  enableTracingAndMetrics: true,
  logLevel: "info",
})
