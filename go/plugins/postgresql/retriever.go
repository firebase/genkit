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

package postgresql

import (
	"context"
	"fmt"
	"slices"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/pgvector/pgvector-go"
)

// RetrieverOptions options for retriever
type RetrieverOptions struct {
	Filter           any
	K                int
	DistanceStrategy DistanceStrategy
}

// Retrieve returns the result of the query
func (ds *DocStore) Retrieve(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
	if req.Options == nil {
		req.Options = &RetrieverOptions{
			Filter:           nil,
			K:                defaultCount,
			DistanceStrategy: defaultDistanceStrategy,
		}
	}

	ropt, ok := req.Options.(*RetrieverOptions)
	if !ok {
		return nil, fmt.Errorf("postgres.Retrieve options have type %T, want %T", req.Options, &RetrieverOptions{})
	}

	if ropt.K <= 0 {
		ropt.K = defaultCount
	}

	if ropt.DistanceStrategy == nil {
		ropt.DistanceStrategy = defaultDistanceStrategy
	}

	ereq := &ai.EmbedRequest{
		Input:   []*ai.Document{req.Query},
		Options: ds.config.EmbedderOptions,
	}

	eres, err := ds.config.Embedder.Embed(ctx, ereq)
	if err != nil {
		return nil, fmt.Errorf("postgres.Retrieve retrieve embedding failed: %v", err)
	}
	res, err := ds.query(ctx, ropt, eres.Embeddings[0].Embedding)
	if err != nil {
		return nil, fmt.Errorf("googlecloudsql.postgres.Retrieve failed to execute the query: %v", err)
	}
	return res, nil
}

func (ds *DocStore) query(ctx context.Context, ropt *RetrieverOptions, embbeding []float32) (*ai.RetrieverResponse, error) {
	res := &ai.RetrieverResponse{}

	query := ds.buildQuery(ropt, embbeding)
	rows, err := ds.engine.Pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	fieldDescriptions := rows.FieldDescriptions()
	columnNames := make([]string, len(fieldDescriptions))

	for i, fieldDescription := range fieldDescriptions {
		columnNames[i] = fieldDescription.Name
	}

	for rows.Next() {
		values := make([]interface{}, len(columnNames))
		valuesPrt := make([]interface{}, len(columnNames))

		for i := range columnNames {
			valuesPrt[i] = &values[i]
		}
		if err := rows.Scan(valuesPrt...); err != nil {
			return nil, fmt.Errorf("scan row failed: %v", err)
		}

		meta := make(map[string]any, ropt.K)
		var content []*ai.Part
		for i, col := range columnNames {
			if (len(ds.config.MetadataColumns) > 0 && !slices.Contains(ds.config.MetadataColumns, col)) &&
				ds.config.ContentColumn != col &&
				ds.config.MetadataJSONColumn != col {
				continue
			}

			if ds.config.ContentColumn == col {
				content = append(content, ai.NewTextPart(values[i].(string)))
			}

			if ds.config.MetadataJSONColumn == col {
				mapMetadata := map[string]any{}
				if values[i] != nil {
					mapMetadata = values[i].(map[string]any)
				}

				meta[col] = mapMetadata
				continue
			}

			meta[col] = values[i]
		}

		doc := &ai.Document{
			Metadata: meta,
			Content:  content,
		}

		res.Documents = append(res.Documents, doc)
	}

	return res, nil
}

func (ds *DocStore) buildQuery(ropt *RetrieverOptions, embedding []float32) string {
	operator := ropt.DistanceStrategy.operator()
	searchFunction := ropt.DistanceStrategy.similaritySearchFunction()
	columns := append(ds.config.MetadataColumns, ds.config.ContentColumn)
	if ds.config.MetadataJSONColumn != "" {
		columns = append(columns, ds.config.MetadataJSONColumn)
	}
	columnNames := strings.Join(columns, `, `)
	whereClause := ""
	if ropt.Filter != nil {
		whereClause = fmt.Sprintf("WHERE %s", ropt.Filter)
	}
	vectorAsString := pgvector.NewVector(embedding).String()
	stmt := fmt.Sprintf(`
        SELECT %s, %s(%s, '%s') AS distance FROM "%s"."%s" %s ORDER BY %s %s '%s' LIMIT %d;`,
		columnNames, searchFunction, ds.config.EmbeddingColumn, vectorAsString, ds.config.SchemaName, ds.config.TableName,
		whereClause, ds.config.EmbeddingColumn, operator, vectorAsString, ropt.K)
	return stmt
}
