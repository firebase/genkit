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
	// An Indexer is used to index documents in a store.
	Indexer core.Action[*IndexerRequest, struct{}, struct{}]
	// A Retriever is used to retrieve indexed documents.
	Retriever core.Action[*RetrieverRequest, *RetrieverResponse, struct{}]
)

type (
	indexerAction   = core.Action[*IndexerRequest, struct{}, struct{}]
	retrieverAction = core.Action[*RetrieverRequest, *RetrieverResponse, struct{}]
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
// [Indexer] that runs it.
func DefineIndexer(provider, name string, index func(context.Context, *IndexerRequest) error) *Indexer {
	f := func(ctx context.Context, req *IndexerRequest) (struct{}, error) {
		return struct{}{}, index(ctx, req)
	}
	return (*Indexer)(core.DefineAction(provider, name, atype.Indexer, nil, f))
}

// LookupIndexer looks up a [Indexer] registered by [DefineIndexer].
// It returns nil if the model was not defined.
func LookupIndexer(provider, name string) *Indexer {
	return (*Indexer)(core.LookupActionFor[*IndexerRequest, struct{}, struct{}](atype.Indexer, provider, name))
}

// DefineRetriever registers the given retrieve function as an action, and returns a
// [Retriever] that runs it.
func DefineRetriever(provider, name string, ret func(context.Context, *RetrieverRequest) (*RetrieverResponse, error)) *Retriever {
	return (*Retriever)(core.DefineAction(provider, name, atype.Retriever, nil, ret))
}

// LookupRetriever looks up a [Retriever] registered by [DefineRetriever].
// It returns nil if the model was not defined.
func LookupRetriever(provider, name string) *Retriever {
	return (*Retriever)(core.LookupActionFor[*RetrieverRequest, *RetrieverResponse, struct{}](atype.Retriever, provider, name))
}

// Index runs the given [Indexer].
func (i *Indexer) Index(ctx context.Context, req *IndexerRequest) error {
	_, err := (*indexerAction)(i).Run(ctx, req, nil)
	return err
}

// Retrieve runs the given [Retriever].
func (r *Retriever) Retrieve(ctx context.Context, req *RetrieverRequest) (*RetrieverResponse, error) {
	return (*retrieverAction)(r).Run(ctx, req, nil)
}

func (i *Indexer) Name() string { return (*indexerAction)(i).Name() }

func (r *Retriever) Name() string { return (*retrieverAction)(r).Name() }
