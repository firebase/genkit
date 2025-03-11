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

package firebase

import (
	"context"
	"fmt"

	"cloud.google.com/go/firestore"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

type VectorType int

const (
	Vector64 VectorType = iota
)

const provider = "firebase"

type RetrieverOptions struct {
	Name            string
	Label           string
	Client          *firestore.Client
	Collection      string
	Embedder        ai.Embedder
	VectorField     string
	MetadataFields  []string
	ContentField    string
	Limit           int
	DistanceMeasure firestore.DistanceMeasure
	VectorType      VectorType
}

func DefineFirestoreRetriever(g *genkit.Genkit, cfg RetrieverOptions) (ai.Retriever, error) {
	if cfg.VectorType != Vector64 {
		return nil, fmt.Errorf("DefineFirestoreRetriever: only Vector64 is supported")
	}
	if cfg.Client == nil {
		return nil, fmt.Errorf("DefineFirestoreRetriever: Firestore client is not provided")
	}

	Retrieve := func(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
		if req.Query == nil {
			return nil, fmt.Errorf("DefineFirestoreRetriever: Request document is nil")
		}

		// Generate query embedding using the Embedder
		embedRequest := &ai.EmbedRequest{Documents: []*ai.Document{req.Query}}
		embedResponse, err := cfg.Embedder.Embed(ctx, embedRequest)
		if err != nil {
			return nil, fmt.Errorf("DefineFirestoreRetriever: Embedding failed: %v", err)
		}

		if len(embedResponse.Embeddings) == 0 {
			return nil, fmt.Errorf("DefineFirestoreRetriever: No embeddings returned")
		}

		queryEmbedding := embedResponse.Embeddings[0].Embedding
		if len(queryEmbedding) == 0 {
			return nil, fmt.Errorf("DefineFirestoreRetriever: Generated embedding is empty")
		}

		// Convert to []float64
		queryEmbedding64 := make([]float64, len(queryEmbedding))
		for i, val := range queryEmbedding {
			queryEmbedding64[i] = float64(val)
		}
		// Perform the FindNearest query
		vectorQuery := cfg.Client.Collection(cfg.Collection).FindNearest(
			cfg.VectorField,
			firestore.Vector64(queryEmbedding64),
			cfg.Limit,
			cfg.DistanceMeasure,
			nil,
		)
		iter := vectorQuery.Documents(ctx)

		results, err := iter.GetAll()
		if err != nil {
			return nil, fmt.Errorf("DefineFirestoreRetriever: FindNearest query failed: %v", err)
		}

		// Prepare the documents to return in the response
		var documents []*ai.Document
		for _, result := range results {
			data := result.Data()

			// Ensure content field exists and is of type string
			content, ok := data[cfg.ContentField].(string)
			if !ok {
				fmt.Printf("Content field %s missing or not a string in document %s", cfg.ContentField, result.Ref.ID)
				continue
			}

			// Extract metadata fields
			metadata := make(map[string]interface{})
			for _, field := range cfg.MetadataFields {
				if value, ok := data[field]; ok {
					metadata[field] = value
				}
			}

			doc := ai.DocumentFromText(content, metadata)
			documents = append(documents, doc)
		}

		return &ai.RetrieverResponse{Documents: documents}, nil
	}

	return genkit.DefineRetriever(g, provider, cfg.Name, Retrieve), nil
}
