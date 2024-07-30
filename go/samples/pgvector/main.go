// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// This program shows how to use Postgres's pgvector extension with Genkit.

// This program can be manually tested like so:
//
// In development mode (with the environment variable GENKIT_ENV="dev"):
// Start the server listening on port 3100:
//
//	go run . -dbconn "$DBCONN" -apikey $API_KEY &
//
// Ask a question:
//
//	curl -d '{"Show": "Best Friends", "Question": "Who does Alice love?"}' http://localhost:3400/askQuestion
package main

import (
	"context"
	"database/sql"
	"errors"
	"flag"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googleai"
	_ "github.com/lib/pq"
	pgv "github.com/pgvector/pgvector-go"
)

var (
	connString = flag.String("dbconn", "", "database connection string")
	apiKey     = flag.String("apikey", "", "Gemini API key")
	index      = flag.Bool("index", false, "index the existing data")
)

func main() {
	flag.Parse()
	if err := run(); err != nil {
		log.Fatal(err)
	}
}

func run() error {
	if *connString == "" {
		return errors.New("need -dbconn")
	}
	if *apiKey == "" {
		return errors.New("need -apikey")
	}
	ctx := context.Background()
	if err := googleai.Init(ctx, &googleai.Config{APIKey: *apiKey}); err != nil {
		return err
	}
	const embedderName = "embedding-001"
	embedder := googleai.Embedder(embedderName)
	if embedder == nil {
		return fmt.Errorf("embedder %s is not known to the googleai plugin", embedderName)
	}

	db, err := sql.Open("postgres", *connString)
	if err != nil {
		return err
	}
	defer db.Close()

	if *index {
		indexer := defineIndexer(db, embedder)
		if err := indexExistingRows(ctx, db, indexer); err != nil {
			return err
		}
	}

	// [START use-retr]
	retriever := defineRetriever(db, embedder)

	type input struct {
		Question string
		Show     string
	}

	genkit.DefineFlow("askQuestion", func(ctx context.Context, in input) (string, error) {
		res, err := retriever.Retrieve(ctx, &ai.RetrieverRequest{
			Document: &ai.Document{Content: []*ai.Part{ai.NewTextPart(in.Question)}},
			Options:  in.Show,
		})
		if err != nil {
			return "", err
		}
		for _, doc := range res.Documents {
			fmt.Printf("%+v %q\n", doc.Metadata, doc.Content[0].Text)
		}
		// Use documents in RAG prompts.
		return "", nil
	})
	// [END use-retr]

	return genkit.Init(ctx, nil)
}

const provider = "pgvector"

// [START retr]
func defineRetriever(db *sql.DB, embedder *ai.Embedder) ai.Retriever {
	f := func(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
		eres, err := embedder.Embed(ctx, &ai.EmbedRequest{Documents: []*ai.Document{req.Document}})
		if err != nil {
			return nil, err
		}
		rows, err := db.QueryContext(ctx, `
			SELECT episode_id, season_number, chunk as content
			FROM embeddings
			WHERE show_id = $1
		  	ORDER BY embedding <#> $2
		  	LIMIT 2`,
			req.Options, pgv.NewVector(eres.Embeddings[0].Embedding))
		if err != nil {
			return nil, err
		}
		defer rows.Close()

		res := &ai.RetrieverResponse{}
		for rows.Next() {
			var eid, sn int
			var content string
			if err := rows.Scan(&eid, &sn, &content); err != nil {
				return nil, err
			}
			meta := map[string]any{
				"episode_id":    eid,
				"season_number": sn,
			}
			doc := &ai.Document{
				Content:  []*ai.Part{ai.NewTextPart(content)},
				Metadata: meta,
			}
			res.Documents = append(res.Documents, doc)
		}
		if err := rows.Err(); err != nil {
			return nil, err
		}
		return res, nil
	}
	return ai.DefineRetriever(provider, "shows", f)
}

// [END retr]

func defineIndexer(db *sql.DB, embedder *ai.Embedder) ai.Indexer {
	// The indexer assumes that each Document has a single part, to be embedded, and metadata fields
	// for the table primary key: show_id, season_number, episode_id.
	const query = `
			UPDATE embeddings
			SET embedding = $4
			WHERE show_id = $1 AND season_number = $2 AND episode_id = $3
		`
	return ai.DefineIndexer(provider, "shows", func(ctx context.Context, req *ai.IndexerRequest) error {
		res, err := embedder.Embed(ctx, &ai.EmbedRequest{Documents: req.Documents})
		if err != nil {
			return err
		}
		// You may want to use your database's batch functionality to insert the embeddings
		// more efficiently.
		for i, emb := range res.Embeddings {
			doc := req.Documents[i]
			args := make([]any, 4)
			for j, k := range []string{"show_id", "season_number", "episode_id"} {
				if a, ok := doc.Metadata[k]; ok {
					args[j] = a
				} else {
					return fmt.Errorf("doc[%d]: missing metadata key %q", i, k)
				}
			}
			args[3] = pgv.NewVector(emb.Embedding)
			if _, err := db.ExecContext(ctx, query, args...); err != nil {
				return err
			}
		}
		return nil
	})
}

func indexExistingRows(ctx context.Context, db *sql.DB, indexer ai.Indexer) error {
	rows, err := db.QueryContext(ctx, `SELECT show_id, season_number, episode_id, chunk FROM embeddings`)
	if err != nil {
		return err
	}
	defer rows.Close()

	req := &ai.IndexerRequest{}
	for rows.Next() {
		var sid, chunk string
		var sn, eid int
		if err := rows.Scan(&sid, &sn, &eid, &chunk); err != nil {
			return err
		}
		req.Documents = append(req.Documents, &ai.Document{
			Content: []*ai.Part{ai.NewTextPart(chunk)},
			Metadata: map[string]any{
				"show_id":       sid,
				"season_number": sn,
				"episode_id":    eid,
			},
		})
	}
	if err := rows.Err(); err != nil {
		return err
	}
	return indexer.Index(ctx, req)
}
