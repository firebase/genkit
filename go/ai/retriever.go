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

package ai

import (
	"context"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
)

type (
	// An IndexerAction is used to index documents in a store.
	IndexerAction = core.Action[*IndexerRequest, struct{}, struct{}]
	// A RetrieverAction is used to retrieve indexed documents.
	RetrieverAction = core.Action[*RetrieverRequest, *RetrieverResponse, struct{}]
)

// IndexerRequest is the data we pass to add documents to the database.
// The Options field is specific to the actual retriever implementation.
type IndexerRequest struct {
	Documents []*Document `json:"docs"`
	Options   any         `json:"options,omitempty"`
}

// RetrieverRequest is the data we pass to retrieve documents from the database.
// The Options field is specific to the actual retriever implementation.
type RetrieverRequest struct {
	Document *Document `json:"content"`
	Options  any       `json:"options,omitempty"`
}

// RetrieverResponse is the response to a document lookup.
type RetrieverResponse struct {
	Documents []*Document `json:"documents"`
}

// DefineIndexer registers the given index function as an action, and returns an
// [IndexerAction] that runs it.
func DefineIndexer(provider, name string, index func(context.Context, *IndexerRequest) error) *IndexerAction {
	f := func(ctx context.Context, req *IndexerRequest) (struct{}, error) {
		return struct{}{}, index(ctx, req)
	}
	return core.DefineAction(provider, name, atype.Indexer, nil, f)
}

// LookupIndexer looks up a [IndexerAction] registered by [DefineIndexer].
// It returns nil if the model was not defined.
func LookupIndexer(provider, name string) *IndexerAction {
	return core.LookupActionFor[*IndexerRequest, struct{}, struct{}](atype.Indexer, provider, name)
}

// DefineRetriever registers the given retrieve function as an action, and returns a
// [RetrieverAction] that runs it.
func DefineRetriever(provider, name string, ret func(context.Context, *RetrieverRequest) (*RetrieverResponse, error)) *RetrieverAction {
	return core.DefineAction(provider, name, atype.Retriever, nil, ret)
}

// LookupRetriever looks up a [RetrieverAction] registered by [DefineRetriever].
// It returns nil if the model was not defined.
func LookupRetriever(provider, name string) *RetrieverAction {
	return core.LookupActionFor[*RetrieverRequest, *RetrieverResponse, struct{}](atype.Retriever, provider, name)
}

// Index runs the given [IndexerAction].
func Index(ctx context.Context, indexer *IndexerAction, req *IndexerRequest) error {
	_, err := indexer.Run(ctx, req, nil)
	return err
}

// Retrieve runs the given [RetrieverAction].
func Retrieve(ctx context.Context, retriever *RetrieverAction, req *RetrieverRequest) (*RetrieverResponse, error) {
	return retriever.Run(ctx, req, nil)
}
