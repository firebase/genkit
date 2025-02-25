<!-- NOTE: prettier-ignore used in some snippets to allow copy/paste into Firebase Functions which
use https://github.com/firebase/firebase-tools/blob/master/templates/init/functions/javascript/_eslintrc -->

# Firebase plugin

The Firebase plugin provides integrations with Firebase services, so you can
build intelligent and scalable AI applications. Key features include:

- **Firestore Vector Store**: Use Firestore for indexing and retrieval
with vector embeddings.
- **Telemetry**: Export telemetry to
[Google's Cloud operations suite](https://cloud.google.com/products/operations)
that powers the Firebase Genkit Monitoring console.

## Installation

Install the Firebase plugin with npm:

```posix-terminal
npm install @genkit-ai/firebase
```

## Prerequisites

### Firebase Project Setup

1. All Firebase products require a Firebase project. You can create a new
   project or enable Firebase in an existing Google Cloud project using the
   [Firebase console](https://console.firebase.google.com/).
1. If deploying flows with Cloud functions,
   [upgrade your Firebase project](https://console.firebase.google.com/project/_/overview?purchaseBillingPlan=metered)
   to the Blaze plan.
1. If you want to run code locally that exports telemetry, you need the
   [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) tool installed.

### Firebase Admin SDK Initialization

You must initialize the Firebase Admin SDK in your application.
This is not handled automatically by the plugin.

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
import { initializeApp } from 'firebase-admin/app';

initializeApp({
  projectId: 'your-project-id',
});
```

The plugin requires you to specify your Firebase project ID. You can specify
your Firebase project ID in either of the following ways:

- Set `projectId` in the `initializeApp()` configuration object as shown
in the snippet above.

- Set the `GCLOUD_PROJECT` environment variable. If you're running your
  flow from a Google Cloud environment (Cloud Functions, Cloud Run, and
  so on), `GCLOUD_PROJECT` is automatically set to the project ID of the
  environment.

  If you set `GCLOUD_PROJECT`, you can omit the configuration
  parameter in `initializeApp()`.

### Credentials

To provide Firebase credentials, you also need to set up Google Cloud
Application Default Credentials. To specify your credentials:

- If you're running your flow from a Google Cloud environment (Cloud Functions,
  Cloud Run, and so on), this is set automatically.

- For other environments:

  1. Generate service account credentials for your Firebase project and
  download the JSON key file. You can do so on the
 [Service account](https://console.firebase.google.com/project/_/settings/serviceaccounts/adminsdk)
  page of the Firebase console.
  1. Set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the file
  path of the JSON file that contains your service account key, or you can set
  the environment variable `GCLOUD_SERVICE_ACCOUNT_CREDS` to the content of the
  JSON file.

## Features and usage

### Telemetry

The Firebase plugin provides a telemetry implementation for sending metrics,
traces, and logs to Firebase Genkit Monitoring.

To get started, visit the [Getting started guide](../observability/getting-started.md)
for installation and configuration instructions.

See the [Authentication and authorization guide](../observability/authentication.md)
to authenticate with Google Cloud.

See the [Advanced configuration guide](../observability/advanced-configuration.md)
for configuration options.

See the [Telemetry collection](../observability/telemetry-collection.md) for
details on which Genkit metrics, traces, and logs collected.

### Cloud Firestore vector search

You can use Cloud Firestore as a vector store for RAG indexing and retrieval.

This section contains information specific to the `firebase` plugin and Cloud
Firestore's vector search feature. See the
[Retrieval-augmented generation](/../rag.md) page for a more detailed
discussion on implementing RAG using Genkit.

#### Using `GCLOUD_SERVICE_ACCOUNT_CREDS` and Firestore

If you are using service account credentials by passing credentials directly
via `GCLOUD_SERVICE_ACCOUNT_CREDS` and are also using Firestore as a vector
store, you need to pass credentials directly to the Firestore instance
during initialization or the singleton may be initialized with application
default credentials depending on plugin initialization order.

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
import {initializeApp} from "firebase-admin/app";
import {getFirestore} from "firebase-admin/firestore";

const app = initializeApp();
let firestore = getFirestore(app);

if (process.env.GCLOUD_SERVICE_ACCOUNT_CREDS) {
  const serviceAccountCreds = JSON.parse(process.env.GCLOUD_SERVICE_ACCOUNT_CREDS);
  const authOptions = { credentials: serviceAccountCreds };
  firestore.settings(authOptions);
}
```

#### Define a Firestore retriever

Use `defineFirestoreRetriever()` to create a retriever for Firestore
vector-based queries.

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
import { defineFirestoreRetriever } from '@genkit-ai/firebase';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

const app = initializeApp();
const firestore = getFirestore(app);

const retriever = defineFirestoreRetriever(ai, {
  name: 'exampleRetriever',
  firestore,
  collection: 'documents',
  contentField: 'text', // Field containing document content
  vectorField: 'embedding', // Field containing vector embeddings
  embedder: yourEmbedderInstance, // Embedder to generate embeddings
  distanceMeasure: 'COSINE', // Default is 'COSINE'; other options: 'EUCLIDEAN', 'DOT_PRODUCT'
});
```

#### Retrieve documents

To retrieve documents using the defined retriever, pass the retriever instance
and query options to `ai.retrieve`.

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
const docs = await ai.retrieve({
  retriever,
  query: 'search query',
  options: {
    limit: 5, // Options: Return up to 5 documents
    where: { category: 'example' }, // Optional: Filter by field-value pairs
    collection: 'alternativeCollection', // Optional: Override default collection
  },
});
```

#### Available Retrieval Options

The following options can be passed to the `options` field in `ai.retrieve`:

- **`limit`**: *(number)*
  Specify the maximum number of documents to retrieve. Default is `10`.

- **`where`**: *(Record\<string, any\>)*
  Add additional filters based on Firestore fields. Example:

  ```js
  where: { category: 'news', status: 'published' }
  ```

- **`collection`**: *(string)*
  Override the default collection specified in the retriever configuration.
- This is useful for querying subcollections or dynamically switching between
- collections.

#### Populate Firestore with Embeddings

To populate your Firestore collection, use an embedding generator along with
the Admin SDK. For example, the menu ingestion script from the
[Retrieval-augmented generation](http://../rag.md) page could be adapted for
Firestore in the following way:

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
import { genkit } from 'genkit';
import { vertexAI, textEmbedding004 } from "@genkit-ai/vertexai";

import { applicationDefault, initializeApp } from "firebase-admin/app";
import { FieldValue, getFirestore } from "firebase-admin/firestore";

import { chunk } from "llm-chunk";
import pdf from "pdf-parse";

import { readFile } from "fs/promises";
import path from "path";

// Change these values to match your Firestore config/schema
const indexConfig = {
  collection: "menuInfo",
  contentField: "text",
  vectorField: "embedding",
  embedder: textEmbedding004,
};

const ai = genkit({
  plugins: [vertexAI({ location: "us-central1" })],
});

const app = initializeApp({ credential: applicationDefault() });
const firestore = getFirestore(app);

export async function indexMenu(filePath: string) {
  filePath = path.resolve(filePath);

  // Read the PDF.
  const pdfTxt = await extractTextFromPdf(filePath);

  // Divide the PDF text into segments.
  const chunks = await chunk(pdfTxt);

  // Add chunks to the index.
  await indexToFirestore(chunks);
}

async function indexToFirestore(data: string[]) {
  for (const text of data) {
    const embedding = (await ai.embed({
      embedder: indexConfig.embedder,
      content: text,
    }))[0].embedding;
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

The prior example requires the `embedding` field to be indexed to work.
To create the index:

- Run the `gcloud` command described in the
[Create a single-field vector index](https://firebase.google.com/docs/firestore/vector-search?authuser=0#create_and_manage_vector_indexes)
section of the Firestore docs.

  The command looks like the following:

  ```posix-terminal
  gcloud alpha firestore indexes composite create --project=your-project-id \
    --collection-group=yourCollectionName --query-scope=COLLECTION \
    --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=yourEmbeddingField
  ```

  However, the correct indexing configuration depends on the queries you
  make and the embedding model you're using.

- Alternatively, call `ai.retrieve()` and Firestore will throw an error with
  the correct command to create the index.

#### Learn more

- See the [Retrieval-augmented generation](http://../rag.md) page for a general discussion
on indexers and retrievers in Genkit.
- See [Search with vector embeddings](https://firebase.google.com/docs/firestore/vector-search)
in the Cloud Firestore docs for more on the vector search feature.

### Deploy flows as Cloud Functions

To deploy a flow with Cloud Functions, use the Firebase Functions library's
built-in support for genkit. The `onCallGenkit` method lets
you to create a [callable function](https://firebase.google.com/docs/functions/callable?gen=2nd)
from a flow. It automatically supports
streaming and JSON requests. You can use the
[Cloud Functions client SDKs](https://firebase.google.com/docs/functions/callable?gen=2nd#call_the_function)
to call them.

<!--See note above on prettier-ignore -->
<!-- prettier-ignore -->
```js
import { onCallGenkit } from 'firebase-functions/https';
import { defineSecret } from 'firebase-functions/params';

export const exampleFlow = ai.defineFlow({
  name: "exampleFlow",
}, async (prompt) => {
    // Flow logic goes here.

    return response;
  }
);

// WARNING: This has no authentication or app check protections.
// See github.com/firebase/genkit/blob/main/docs/auth.md for more information.
export const example = onCallGenkit({ secrets: [apiKey] }, exampleFlow);
```

Deploy your flow using the Firebase CLI:

```posix-terminal
firebase deploy --only functions
```