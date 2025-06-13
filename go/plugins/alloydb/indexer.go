// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// You may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package alloydb

import (
	"context"
	"encoding/json"
	"fmt"
	"slices"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/pgvector/pgvector-go"
)

// Index is used to index documents .
func (ds *DocStore) Index(ctx context.Context, req *ai.IndexerRequest) error {
	if len(req.Documents) == 0 {
		return nil
	}

	ereq := &ai.EmbedRequest{
		Input:   req.Documents,
		Options: ds.config.EmbedderOptions,
	}
	eres, err := ds.config.Embedder.Embed(ctx, ereq)
	if err != nil {
		return fmt.Errorf("postgres.Indexer index embedding failed: %v", err)
	}

	b := &pgx.Batch{}

	for i, doc := range req.Documents {
		// if no metadata provided, initialize with empty map
		if doc.Metadata == nil {
			doc.Metadata = make(map[string]any)
		}

		// generate the id if it's not defined
		_, okString := doc.Metadata[ds.config.IDColumn].(string)
		idBytes, okBytes := doc.Metadata[ds.config.IDColumn].([]byte) // represents the uuid

		if !okString && !okBytes {
			doc.Metadata[ds.config.IDColumn] = uuid.New().String()
		}

		if okBytes {
			doc.Metadata[ds.config.IDColumn] = string(idBytes)
		}

		doc.Metadata[ds.config.ContentColumn] = ""
		if len(doc.Content) > 0 {
			doc.Metadata[ds.config.ContentColumn] = doc.Content[0].Text
		}

		embeddingString := pgvector.NewVector(eres.Embeddings[i].Embedding).String()
		query, values, err := ds.generateAddDocumentsQuery(
			doc.Metadata[ds.config.IDColumn].(string),
			doc.Metadata[ds.config.ContentColumn].(string),
			embeddingString,
			doc.Metadata)
		if err != nil {
			return err
		}
		b.Queue(query, values...)
	}

	batchResults := ds.engine.Pool.SendBatch(ctx, b)
	if err := batchResults.Close(); err != nil {
		return fmt.Errorf("failed to execute batch: %w", err)
	}

	return nil
}

func (ds *DocStore) generateAddDocumentsQuery(id, content, embedding string, metadata map[string]any) (string, []any, error) {
	// Construct metadata column names if present
	metadataColNames := ""
	if len(ds.config.MetadataColumns) > 0 {
		metadataColNames = ", " + strings.Join(ds.config.MetadataColumns, ", ")
	}

	if ds.config.MetadataJSONColumn != "" && !slices.Contains(ds.config.MetadataColumns, ds.config.MetadataJSONColumn) {
		metadataColNames += ", " + ds.config.MetadataJSONColumn
	}

	insertStmt := fmt.Sprintf(`INSERT INTO %q.%q (%s, %s, %s%s)`,
		ds.config.SchemaName, ds.config.TableName, ds.config.IDColumn, ds.config.ContentColumn, ds.config.EmbeddingColumn, metadataColNames)
	valuesStmt := " VALUES ($1, $2, $3"
	values := []any{id, content, embedding}

	// Add metadata
	for _, metadataColumn := range ds.config.MetadataColumns {
		if val, ok := metadata[metadataColumn]; ok {
			valuesStmt += fmt.Sprintf(", $%d", len(values)+1)
			values = append(values, val)
			delete(metadata, metadataColumn)
		} else {
			valuesStmt += ", NULL"
		}
	}
	// Add JSON column and/or close statement
	if ds.config.MetadataJSONColumn != "" && !slices.Contains(ds.config.MetadataColumns, ds.config.MetadataJSONColumn) {
		valuesStmt += fmt.Sprintf(", $%d", len(values)+1)
		metadataJSON, err := json.Marshal(metadata)
		if err != nil {
			return "", nil, fmt.Errorf("failed to transform metadata to json: %w", err)
		}
		values = append(values, metadataJSON)
	}
	valuesStmt += ")"
	query := insertStmt + valuesStmt
	return query, values, nil
}
