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

type RetrieverOptions struct {
	Name            string
	Label           string
	Client          *firestore.Client
	Embedder        ai.Embedder
	EmbedderOptions ai.EmbedOption
	Collection      string
	VectorField     string
	MetadataField   string
	ContentField    string
	DistanceMeasure firestore.DistanceMeasure
}

type RetrieverRequestOptions struct {
	Limit           int `json:"limit,omitempty"` // maximum number of values to retrieve
	DistanceMeasure firestore.DistanceMeasure
}

func DefineFirestoreRetriever(cfg RetrieverOptions) (ai.Retriever, error) {

	Retrieve := func(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
		options := RetrieverRequestOptions{Limit: 10, DistanceMeasure: cfg.DistanceMeasure}

		if req.Options != nil {
			// Ensure that the options are of the correct type
			parsedOptions, ok := req.Options.(RetrieverRequestOptions)
			if !ok {
				return nil, fmt.Errorf("firebase.Retrieve options have type %T, want %T", req.Options, &RetrieverRequestOptions{})
			}
			options = parsedOptions
		}

		// Use the embedder to convert the document we want to retrieve into a vector.
		ereq := &ai.EmbedRequest{
			Documents: []*ai.Document{req.Document},
			Options:   cfg.EmbedderOptions,
		}

		eres, err := cfg.Embedder.Embed(ctx, ereq)
		if err != nil {
			return nil, fmt.Errorf("%s index embedding failed: %v", provider, err)
		}

		coll := cfg.Client.Collection(cfg.Collection)
		embedding := eres.Embeddings[0].Embedding

		distanceMeasure := options.DistanceMeasure | cfg.DistanceMeasure

		query := coll.FindNearest(cfg.VectorField, embedding, options.Limit, distanceMeasure, nil)

		// Execute the query
		iter := query.Documents(ctx)
		gotDocs, _ := iter.GetAll()

		genkitDocs := make([]*ai.Document, len(gotDocs))
		for i, doc := range gotDocs {
			content := doc.Data()[cfg.ContentField].(string)
			metadata := doc.Data()[cfg.MetadataField].(map[string]any)
			genkitDocs[i] = ai.DocumentFromText(content, metadata)
		}

		return &ai.RetrieverResponse{Documents: genkitDocs}, nil
	}

	return ai.DefineRetriever(provider, cfg.Name, Retrieve), nil
}
