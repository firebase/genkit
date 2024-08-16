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
)

const provider = "firebase"

// RetrieverOptions defines the configuration for the retriever.
type RetrieverOptions struct {
	Name            string
	Label           string
	Client          *firestore.Client
	Embedder        ai.Embedder
	EmbedderOptions ai.EmbedOption
	Collection      string
	VectorField     string
	MetadataFields  []string // Optional: if empty, metadata will not be retrieved
	ContentField    string
	DistanceMeasure firestore.DistanceMeasure
}

type RetrieverRequestOptions struct {
	Limit           int `json:"limit,omitempty"` // maximum number of values to retrieve
	DistanceMeasure firestore.DistanceMeasure
}

func DefineFirestoreRetriever(cfg RetrieverOptions) (ai.Retriever, error) {

	Retrieve := func(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
		if req == nil {
			return nil, fmt.Errorf("retriever request is nil")
		}

		options := RetrieverRequestOptions{Limit: 10, DistanceMeasure: cfg.DistanceMeasure}

		if req.Options != nil {
			// Ensure that the options are of the correct type
			parsedOptions, ok := req.Options.(RetrieverRequestOptions)
			if !ok {
				return nil, fmt.Errorf("firebase.Retrieve options have type %T, want %T", req.Options, &RetrieverRequestOptions{})
			}
			options = parsedOptions
		}

		if cfg.Embedder == nil {
			return nil, fmt.Errorf("embedder is nil in config")
		}

		// Use the embedder to convert the document we want to retrieve into a vector.
		ereq := &ai.EmbedRequest{
			Documents: []*ai.Document{req.Document},
		}

		eres, err := cfg.Embedder.Embed(ctx, ereq)
		if err != nil {
			return nil, fmt.Errorf("%s index embedding failed: %v", provider, err)
		}

		if eres == nil || len(eres.Embeddings) == 0 {
			return nil, fmt.Errorf("embedding result is nil or empty")
		}

		coll := cfg.Client.Collection(cfg.Collection)
		if coll == nil {
			return nil, fmt.Errorf("collection is nil")
		}

		embedding := eres.Embeddings[0].Embedding

		distanceMeasure := options.DistanceMeasure | cfg.DistanceMeasure

		query := coll.FindNearest(cfg.VectorField, embedding, options.Limit, distanceMeasure, nil)

		// Execute the query
		iter := query.Documents(ctx)
		if iter == nil {
			return nil, fmt.Errorf("document iterator is nil")
		}

		gotDocs, err := iter.GetAll()

		if err != nil {
			return nil, fmt.Errorf("failed to get documents: %v", err)
		}

		genkitDocs := make([]*ai.Document, len(gotDocs))

		for i, doc := range gotDocs {
			content, ok := doc.Data()[cfg.ContentField].(string)
			if !ok {
				fmt.Printf("content field is missing or not a string in document %v", doc.Ref.ID)
				continue
			}

			out := make(map[string]any)
			out["content"] = content

			metadata := make(map[string]any)
			if len(cfg.MetadataFields) > 0 {
				for _, field := range cfg.MetadataFields {
					metadata[field] = doc.Data()[field]
				}
			} else {
				for k, v := range doc.Data() {
					if k != cfg.VectorField && k != cfg.ContentField {
						metadata[k] = v
					}
				}
			}

			out["metadata"] = metadata
			genkitDocs[i] = ai.DocumentFromText(content, metadata)
		}

		return &ai.RetrieverResponse{Documents: genkitDocs}, nil
	}

	return ai.DefineRetriever(provider, cfg.Name, Retrieve), nil
}
