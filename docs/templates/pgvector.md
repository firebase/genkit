# pgvector retriever template

You can use PostgreSQL and `pgvector` as your retriever implementation. Use the
following examples as a starting point and modify it to work with your database
schema.

For the Golang snippet, we use [pgx](https://github.com/jackc/pgx) as the
Postgres client, but you may use another client libaray of your choice.

<section>
  <devsite-selector>
    <section>
      <h3>Node.js (Typescript)</h3>
      <p>```js
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
                const results = await sql
                  SELECT episode_id, season_number, chunk as content
                    FROM embeddings
                    WHERE show_id = ${options.show}
                    ORDER BY embedding <#> ${toSql(embedding)} LIMIT ${options.k ?? 3}
                 ;
                return {
                  documents: results.map((row) => {
                    const { content, ...metadata } = row;
                    return Document.fromText(content, metadata);
                  }),
                };
              }
            );
            ```
      </p>
    </section>
    <section>
      <h3>Go</h3>
      <p>
      ```go
      package main

      import (
        "context"
        "fmt"
        "os"

      )

      import (
        "context"
        "fmt"
        "log"
        "os"

        "github.com/firebase/genkit/go/ai"
        "github.com/firebase/genkit/go/plugins/googleai"
        "github.com/jackc/pgx/v5"
        "github.com/pgvector/pgvector-go"
      )

      func retrieve(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
        // urlExample := "postgres://username:password@localhost:5432/database_name"
        conn, err := pgx.Connect(context.Background(), os.Getenv("DATABASE_URL"))
        if err != nil {
          return nil, fmt.Errorf( "Unable to connect to database: %v\n", err)
        }
        defer conn.Close(context.Background())

        // Use the embedder to convert the document we want to
        // retrieve into a vector.
        ereq := &ai.EmbedRequest{
          Document: req.Document,
        }
        embedder := googleai.Embedder("embedding-001")
        vals, err := embedder.Embed(ctx, ereq)
        if err != nil {
          return nil, fmt.Errorf("embedding failed: %v", err)
        }

        k := 3
        if options, _ := req.Options.(*RetrieverOptions); options != nil {
          k = options.K
        }

        rows, err := conn.Query(context.Background(), "SELECT chunk as content FROM embeddings WHERE show_id = $1 ORDER BY embedding <#> $2 LIMIT $3", "game_of_thrones", pgvector.NewVector(vals), k)
        if err != nil {
          return nil, fmt.Errorf("Query failed: %v\n", err)
        }

        docs := make([]*ai.Document, 0, 3)

        for rows.Next() {
          var content string
          rows.Scan(&content)
          docs = append(docs, ai.DocumentFromText(content, nil))
        }

        resp := &ai.RetrieverResponse{
          Documents: docs,
        }
        return resp, nil
      }


      func main() {
        // ... Configure genkit

        provider := "pgvector"
        name := "tvShows"
        retriever := ai.DefineRetriever(provider, name, retrieve)
      }
      ```
      </p>
    </section>

  </devsite-selector>
</section>

And here's how to use the retriever in a flow:

<section>
  <devsite-selector>
    <section>
      <h3>Node.js (Typescript)</h3>
      <p>
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
      </p>
    </section>
    <section>
      <h3>Go</h3>
      <p>
        ```go
        func main() {
          // ...
          // Setup genkit and get the pgvector retriever as shown above

          // Use your retriever.
          tvShowSuggestionFlow := genkit.DefineFlow(
          "tvShowSuggestionFlow",
          func(ctx context.Context, inputQuery string) (string, error) {
            dRequest := ai.DocumentFromText(inputQuery, nil)
            retrieverReq := &ai.RetrieverRequest{
              Document: dRequest,
            }
            response, err := retriever.Retrieve(ctx, retrieverReq)
            if err != nil {
              return "", err
            }

            // Use retrieved docs in `response` for RAG
            // ...

            return suggestion, nil
          },
        )
        }
        ```
      </p>
    </section>

  </devsite-selector>
</section>
