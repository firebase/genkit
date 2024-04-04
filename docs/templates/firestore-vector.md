# Firestore vector store template

You can use Firestore vector store in Genkit to power your RAG flows by storing and retrieving embedding vectors.

Here is a sample template which retrieves documents from Firestore.

Use the following example as a starting point and modify it to work with your database layout.
This sample assumes that you already have a Firestore collection called `vectors` in which each document
has an `embedding` field that stores the embedding vector.

Important: Vector support is available only in `@google-cloud/firestore` versions starting from `7.6.0`. You must update your dependecies to match this version.

Firestore depends on indices to provide fast and efficient querying on collections. This sample requires the `embedding` field to be indexed to work. To do so, invoke the
flow and Firestore will throw an error with a command to create an index. Execute that command
and your index should be ready to use.

```js
import { embed } from '@genkit-ai/ai/embedder';
import { Document, defineRetriever } from '@genkit-ai/ai/retriever';
import { textEmbeddingGecko } from '@genkit-ai/vertexai';
import {
  FieldValue,
  VectorQuery,
  VectorQuerySnapshot,
} from '@google-cloud/firestore';
import { Firestore } from 'firebase-admin/firestore';
import * as z from 'zod';
import { augmentedPrompt } from './prompt';

const QueryOptions = z.object({
  k: z.number().optional(),
});

const firestoreArtifactsRetriever = defineRetriever(
  {
    name: 'firestore/artifacts',
    configSchema: QueryOptions,
  },
  async (input, options) => {
    const embedding = await embed({
      embedder: textEmbeddingGecko,
      content: input,
    });

    const db = new Firestore();
    const coll = db.collection('vectors' /* your collection name */);

    const vectorQuery: VectorQuery = coll.findNearest(
      'embedding' /* the name of the field that contains the vector */,
      FieldValue.vector(embedding),
      {
        limit: options.k ?? 3,
        distanceMeasure: 'COSINE',
      }
    );

    const vectorQuerySnapshot: VectorQuerySnapshot = await vectorQuery.get();
    return {
      documents: vectorQuerySnapshot.docs.map((doc) =>
        // doc.data() represents the Firestore document. You may process it as needed to generate
        // a Genkit document object, depending on your storage format.
        Document.fromText(doc.data().content.text)
      ),
    };
  }
);
```

And here's how to use the retriever in a flow:

```js
// Simple flow to use the firestoreArtifactsRetriever
export const askQuestionsOnNewsArticles = defineFlow(
  {
    name: 'askQuestionsOnNewsArticles',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (inputQuestion) => {
    const docs = await retrieve({
      retriever: firestoreArtifactsRetriever,
      query: inputQuestion,
      options: {
        k: 5,
      },
    });
    console.log(docs);

    // Continue with using retrieved docs
    // in RAG prompts.
    //...
  }
);
```
