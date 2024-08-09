<!-- NOTE: prettier-ignore used in some snippets to allow copy/paste into Firebase Functions which
use https://github.com/firebase/firebase-tools/blob/master/templates/init/functions/javascript/_eslintrc -->

# Firebase plugin

The Firebase plugin provides several integrations with Firebase services:

- Indexers and retrievers using Cloud Firestore vector store
- Trace storage using Cloud Firestore
- Flow deployment using Cloud Functions
- Authorization policies for Firebase Authentication users

<!-- - State storage using Cloud Firestore -->

## Installation

```posix-terminal
npm i --save @genkit-ai/firebase
```

## Prerequisites

- All Firebase products require a Firebase project. You can create a new project
  or enable Firebase in an existing Google Cloud project using the
  [Firebase console](https://console.firebase.google.com/).
- In addition, if you want to deploy flows to Cloud Functions, you must
  [upgrade your project](https://console.firebase.google.com/project/_/overview?purchaseBillingPlan=metered)
  to the Blaze pay-as-you-go plan.

## Configuration

### Project ID

To use this plugin, specify it when you call `configureGenkit()`:

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
import {configureGenkit} from "@genkit-ai/core";
import {firebase} from "@genkit-ai/firebase";

configureGenkit({
  plugins: [firebase({projectId: "your-firebase-project"})],
});
```

The plugin requires you to specify your Firebase project ID. You can specify
your Firebase project ID in either of the following ways:

- Set `projectId` in the `firebase()` configuration object.

- Set the `GCLOUD_PROJECT` environment variable. If you're running your flow
  from a Google Cloud environment (Cloud Functions, Cloud Run, and so on),
  `GCLOUD_PROJECT` is automatically set to the project ID of the environment.

  If you set `GCLOUD_PROJECT`, you can omit the configuration parameter:
  `firebase()`

### Credentials

To provide Firebase credentials, you also need to set up Google Cloud
Application Default Credentials. To specify your credentials:

- If you're running your flow from a Google Cloud environment (Cloud Functions,
  Cloud Run, and so on), this is set automatically.

- For other environments:

  1.  Generate service account credentials for your Firebase project and
      download the JSON key file. You can do so on the
      [Service account](https://console.firebase.google.com/project/_/settings/serviceaccounts/adminsdk)
      page of the Firebase console.
  1.  Set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the file
      path of the JSON file that contains your service account key, or you can set the environment variable `GCLOUD_SERVICE_ACCOUNT` to the content of the JSON file.

### Telemetry

The plugin has a direct dependency on the [Google Cloud plugin](google-cloud.md) and thus has provisions to enable telemetry export to Google's Cloud operations suite. To enable telemetry export, set the `enableTracingAndMetrics` to `true` and add a telemetry section to the Genkit configuration:

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
import {configureGenkit} from "@genkit-ai/core";
import {firebase} from "@genkit-ai/firebase";

configureGenkit({
  plugins: [firebase()],
  enableTracingAndMetrics: true,
  telemetry: {
    instrumentation: 'firebase',
    logger: 'firebase',
  },
});
```

Refer the the [Google Cloud plugin](google-cloud.md) documentation for all configuration options and the necessary APIs that need to be enabled on the project.

## Usage

This plugin provides several integrations with Firebase services, which you can
use together or individually.

### Cloud Firestore vector store

You can use Cloud Firestore as a vector store for RAG indexing and retrieval.

This section contains information specific to the `firebase` plugin and Cloud
Firestore's vector search feature.
See the [Retrieval-augmented generation](../rag.md) page for a more detailed
discussion on implementing RAG using Genkit.

#### Using GCLOUD_SERVICE_ACCOUNT and Firestore 

If you are using service account credentials by passing credentials directly via `GCLOUD_SERVICE_ACCOUNT` and are also using Firestore as a vector store, you will need to pass credentials directly to the Firestore instance during initialization or the singleton may be initialized with application default credentials depending on plugin initialization order.

```
import {initializeApp} from "firebase-admin/app";
import {getFirestore} from "firebase-admin/firestore";

const app = initializeApp();
let firestore = getFirestore(app);

if (process.env.GCLOUD_SERVICE_ACCOUNT) {
  const serviceAccountCreds = JSON.parse(process.env.GCLOUD_SERVICE_ACCOUNT);
  const authOptions = { credentials: serviceAccountCreds };
  firestore.settings(authOptions);
}
```

#### Retrievers

The `firebase` plugin provides a convenience function for defining Firestore
retrievers, `defineFirestoreRetriever()`:

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
import {defineFirestoreRetriever} from "@genkit-ai/firebase";
import {retrieve} from "@genkit-ai/ai/retriever";

import {initializeApp} from "firebase-admin/app";
import {getFirestore} from "firebase-admin/firestore";

const app = initializeApp();
const firestore = getFirestore(app);

const yourRetrieverRef = defineFirestoreRetriever({
  name: "yourRetriever",
  firestore: getFirestore(app),
  collection: "yourCollection",
  contentField: "yourDataChunks",
  vectorField: "embedding",
  embedder: textEmbeddingGecko, // Import from '@genkit-ai/googleai' or '@genkit-ai/vertexai'
  distanceMeasure: "COSINE", // "EUCLIDEAN", "DOT_PRODUCT", or "COSINE" (default)
});
```

To use it, pass it to the `retrieve()` function:

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
const docs = await retrieve({
  retriever: yourRetrieverRef,
  query: "look for something",
  options: {limit: 5},
});
```

Available retrieval options include:

- `limit`: Specify the number of matching results to return.
- `where`: Field/value pairs to match (e.g. `{category: 'food'}`) in addition to vector search.
- `collection`: Override the default collection to search for e.g. subcollection search.

#### Indexing and Embedding

To populate your Firestore collection, use an embedding generator along with the
Admin SDK. For example, the menu ingestion script from the
[Retrieval-augmented generation](../rag.md) page could be adapted for Firestore
in the following way:

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```ts
import { configureGenkit } from "@genkit-ai/core";
import { embed } from "@genkit-ai/ai/embedder";
import { defineFlow, run } from "@genkit-ai/flow";
import { textEmbeddingGecko, vertexAI } from "@genkit-ai/vertexai";

import { applicationDefault, initializeApp } from "firebase-admin/app";
import { FieldValue, getFirestore } from "firebase-admin/firestore";

import { chunk } from "llm-chunk";
import pdf from "pdf-parse";
import * as z from "zod";

import { readFile } from "fs/promises";
import path from "path";

// Change these values to match your Firestore config/schema
const indexConfig = {
  collection: "menuInfo",
  contentField: "text",
  vectorField: "embedding",
  embedder: textEmbeddingGecko,
};

configureGenkit({
  plugins: [vertexAI({ location: "us-central1" })],
  enableTracingAndMetrics: false,
});

const app = initializeApp({ credential: applicationDefault() });
const firestore = getFirestore(app);

export const indexMenu = defineFlow(
  {
    name: "indexMenu",
    inputSchema: z.string().describe("PDF file path"),
    outputSchema: z.void(),
  },
  async (filePath: string) => {
    filePath = path.resolve(filePath);

    // Read the PDF.
    const pdfTxt = await run("extract-text", () =>
      extractTextFromPdf(filePath)
    );

    // Divide the PDF text into segments.
    const chunks = await run("chunk-it", async () => chunk(pdfTxt));

    // Add chunks to the index.
    await run("index-chunks", async () => indexToFirestore(chunks));
  }
);

async function indexToFirestore(data: string[]) {
  for (const text of data) {
    const embedding = await embed({
      embedder: indexConfig.embedder,
      content: text,
    });
    await firestore.collection(indexConfig.collection).add({
      [indexConfig.vectorField]: FieldValue.vector(embedding),
      [indexConfig.contentField]: text,
    });
  }
}

async function extractTextFromPdf(filePath: string) {
  const pdfFile = path.resolve(filePath);
  const dataBuffer = await readFile(pdfFile);
  const data = await pdf(dataBuffer);
  return data.text;
}
```

Firestore depends on indexes to provide fast and efficient querying on
collections. (Note that "index" here refers to database indexes, and not
Genkit's indexer and retriever abstractions.)

The prior example requires the `embedding` field to be indexed to
work. To create the index:

- Run the `gcloud` command described in the
  [Create a single-field vector index](https://firebase.google.com/docs/firestore/vector-search?authuser=0#create_and_manage_vector_indexes)
  section of the Firestore docs.

  The command looks like the following:

  ```posix-terminal
  gcloud alpha firestore indexes composite create --project=your-project-id \
    --collection-group=yourCollectionName --query-scope=COLLECTION \
    --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=yourEmbeddingField
  ```

  However, the correct indexing configuration depends on the queries you will
  make and the embedding model you're using.

- Alternatively, call `retrieve()` and Firestore will throw an error with the
  correct command to create the index.

#### Learn more

- See the [Retrieval-augmented generation](../rag.md) page for a general
  discussion on indexers and retrievers in Genkit.
- See [Search with vector embeddings](https://firebase.google.com/docs/firestore/vector-search)
  in the Cloud Firestore docs for more on the vector search feature.

### Cloud Firestore trace storage

You can use Cloud Firestore to store traces:

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
import {firebase} from "@genkit-ai/firebase";

configureGenkit({
  plugins: [firebase()],
  traceStore: "firebase",
  enableTracingAndMetrics: true,
});
```

By default, the plugin stores traces in a collection called `genkit-traces` in
the project's default database. To change either setting:

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
firebase({
  traceStore: {
    collection: "your-collection";
    databaseId: "your-db";
  }
})
```

When using Firestore-based trace storage you will want to enable TTL for the trace documents: https://firebase.google.com/docs/firestore/ttl

### Cloud Functions

The plugin provides the `onFlow()` constructor, which creates a flow backed by a
Cloud Functions for Firebase HTTPS-triggered function. These functions conform
to Firebase's
[callable function interface](https://firebase.google.com/docs/functions/callable-reference) and you can use the
[Cloud Functions client SDKs](https://firebase.google.com/docs/functions/callable?gen=2nd#call_the_function)
to call them.

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
import {firebase} from "@genkit-ai/firebase";
import {onFlow, noAuth} from "@genkit-ai/firebase/functions";

configureGenkit({
  plugins: [firebase()],
});

export const exampleFlow = onFlow(
  {
    name: "exampleFlow",
    authPolicy: noAuth(), // WARNING: noAuth() creates an open endpoint!
  },
  async (prompt) => {
    // Flow logic goes here.

    return response;
  }
);
```

Deploy your flow using the Firebase CLI:

```posix-terminal
firebase deploy --only functions
```

The `onFlow()` function has some options not present in `defineFlow()`:

- `httpsOptions`: an [`HttpsOptions`](https://firebase.google.com/docs/reference/functions/2nd-gen/node/firebase-functions.https.httpsoptions)
  object used to configure your Cloud Function:

  <!--See note above on prettier-ignore -->
  <!-- prettier-ignore -->
  ```js
  export const exampleFlow = onFlow(
    {
      name: "exampleFlow",
      httpsOptions: {
        cors: true,
      },
      // ...
    },
    async (prompt) => {
      // ...
    }
  );
  ```

- `enforceAppCheck`: when `true`, reject requests with missing or invalid [App Check](https://firebase.google.com/docs/app-check)
  tokens.

- `consumeAppCheckToken`: when `true`, invalidate the App Check token after verifying it.

  See [Replay protection](https://firebase.google.com/docs/app-check/cloud-functions#replay-protection).

### Firebase Auth

This plugin provides a helper function to create authorization policies around
Firebase Auth:

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
import {firebaseAuth} from "@genkit-ai/firebase/auth";

export const exampleFlow = onFlow(
  {
    name: "exampleFlow",
    authPolicy: firebaseAuth((user) => {
      if (!user.email_verified) throw new Error("Requires verification!");
    }),
  },
  async (prompt) => {
    // ...
  }
);
```

To define an auth policy, provide `firebaseAuth()` with a callback function that
takes a
[`DecodedIdToken`](https://firebase.google.com/docs/reference/admin/node/firebase-admin.auth.decodedidtoken)
as its only parameter. In this function, examine the user token and throw an
error if the user fails to meet any of the criteria you want to require.

See [Authorization and integrity](../auth.md) for a more thorough discussion of
this topic.
