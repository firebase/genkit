# PGVector retriever

Here is an example of how you can use the Genkit framework to 
defined your own pgvector-based retriever for a Postgres DB.

```javascript
import {
  TextDocumentSchema,
  defineRetriever,
  retrieve,
} from '@google-genkit/ai/retrievers';
import { z } from 'zod';
import postgres from 'postgres';
import { embed } from '@google-genkit/ai/embedders';
import { textembeddingGecko } from '@google-genkit/plugin-vertex-ai';
import './genkit.conf';
import { toSql } from 'pgvector';

const sql = postgres({ ssl: false, database: 'recaps' });

const sqlRetriever = defineRetriever(
  {
    provider: 'custom',
    retrieverId: 'sql',
    customOptionsType: z.any(),
    documentType: TextDocumentSchema,
    queryType: z.object({
      show: z.string(),
      question: z.string(),
    }),
  },
  async (input) => {
    const embedding = await embed({
      embedder: textembeddingGecko,
      input: input.question,
    });
    const results = await sql`
      SELECT episode_id, season_number, chunk as content
        FROM embeddings
        WHERE show_id = ${input.show}
        ORDER BY embedding <#> ${toSql(embedding)} LIMIT 5
      `;
    return results.map((row) => {
      const { content, ...metadata } = row;
      return { content, metadata };
    });
  }
);


// Simple flow to use the sqlRetriever
export const askQuestionsOnGoT = flow(
  {
    name: 'askQuestionsOnGoT',
    input: z.string(),
    output: z.string(),
  },
  async (inputQuestion) => {
    const docs = await retrieve({
      retriever: sqlRetriever,
      query: {
        show: "Game of Thrones",
        question: inputQuestion,
      }
    });
    console.log(docs);

    // Continue with using retrieved docs 
    // in RAG prompts.
    ... 
  }
);
```