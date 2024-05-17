# pgvector retriever template

You can use PostgreSQL and `pgvector` as your retriever implementation. Use the
following example as a starting point and modify it to work with your database
schema.

```js
import { embed } from '@genkit-ai/ai/embedder';
import { Document, defineRetriever, retrieve } from '@genkit-ai/ai/retriever';
import { defineFlow } from '@genkit-ai/flow';
import { textEmbeddingGecko } from '@genkit-ai/vertexai';
import { toSql } from 'pgvector';
import postgres from 'postgres';
import { z } from 'zod';

const sql = postgres({ ssl: false, database: 'recaps' });

const QueryOptions = z.object({
  show: z.string(),
  k: z.number().optional(),
});

const sqlRetriever = defineRetriever(
  {
    name: 'pgvector-myTable',
    configSchema: QueryOptions,
  },
  async (input, options) => {
    const embedding = await embed({
      embedder: textEmbeddingGecko,
      content: input,
    });
    const results = await sql`
      SELECT episode_id, season_number, chunk as content
        FROM embeddings
        WHERE show_id = ${options.show}
        ORDER BY embedding <#> ${toSql(embedding)} LIMIT ${options.k ?? 3}
      `;
    return {
      documents: results.map((row) => {
        const { content, ...metadata } = row;
        return Document.fromText(content, metadata);
      }),
    };
  }
);
```

And here's how to use the retriever in a flow:

```js
// Simple flow to use the sqlRetriever
export const askQuestionsOnGoT = defineFlow(
  {
    name: 'askQuestionsOnGoT',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (inputQuestion) => {
    const docs = await retrieve({
      retriever: sqlRetriever,
      query: inputQuestion,
      options: {
        show: 'Game of Thrones',
      },
    });
    console.log(docs);

    // Continue with using retrieved docs
    // in RAG prompts.
    //...
  }
);
```
