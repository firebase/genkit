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
	"errors"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
)

// Retriever represents a document retriever.
type Retriever interface {
	// Name returns the name of the retriever.
	Name() string
	// Retrieve retrieves the documents.
	Retrieve(ctx context.Context, req *RetrieverRequest) (*RetrieverResponse, error)
}

// Indexer represents a document retriever.
type Indexer interface {
	// Name returns the name of the indexer.
	Name() string
	// Index executes the indexing request.
	Index(ctx context.Context, req *IndexerRequest) error
}

type (
	indexerActionDef   core.Action[*IndexerRequest, struct{}, struct{}]
	retrieverActionDef core.Action[*RetrieverRequest, *RetrieverResponse, struct{}]

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
func DefineIndexer(provider, name string, index func(context.Context, *IndexerRequest) error) Indexer {
	f := func(ctx context.Context, req *IndexerRequest) (struct{}, error) {
		return struct{}{}, index(ctx, req)
	}
	return (*indexerActionDef)(core.DefineAction(provider, name, atype.Indexer, nil, f))
}

// IsDefinedIndexer reports whether an [Indexer] is defined.
func IsDefinedIndexer(provider, name string) bool {
	return (*indexerActionDef)(core.LookupActionFor[*IndexerRequest, struct{}, struct{}](atype.Indexer, provider, name)) != nil
}

// LookupIndexer looks up an [Indexer] registered by [DefineIndexer].
// It returns nil if the model was not defined.
func LookupIndexer(provider, name string) Indexer {
	return (*indexerActionDef)(core.LookupActionFor[*IndexerRequest, struct{}, struct{}](atype.Indexer, provider, name))
}

// DefineRetriever registers the given retrieve function as an action, and returns a
// [Retriever] that runs it.
func DefineRetriever(provider, name string, ret func(context.Context, *RetrieverRequest) (*RetrieverResponse, error)) *retrieverActionDef {
	return (*retrieverActionDef)(core.DefineAction(provider, name, atype.Retriever, nil, ret))
}

// IsDefinedRetriever reports whether a [Retriever] is defined.
func IsDefinedRetriever(provider, name string) bool {
	return (*retrieverActionDef)(core.LookupActionFor[*RetrieverRequest, *RetrieverResponse, struct{}](atype.Retriever, provider, name)) != nil
}

// LookupRetriever looks up a [Retriever] registered by [DefineRetriever].
// It returns nil if the model was not defined.
func LookupRetriever(provider, name string) Retriever {
	return (*retrieverActionDef)(core.LookupActionFor[*RetrieverRequest, *RetrieverResponse, struct{}](atype.Retriever, provider, name))
}

// Index runs the given [Indexer].
func (i *indexerActionDef) Index(ctx context.Context, req *IndexerRequest) error {
	if i == nil {
		return errors.New("Index called on a nil Indexer; check that all indexers are defined")
	}
	_, err := (*indexerAction)(i).Run(ctx, req, nil)
	return err
}

// Retrieve runs the given [Retriever].
func (r *retrieverActionDef) Retrieve(ctx context.Context, req *RetrieverRequest) (*RetrieverResponse, error) {
	if r == nil {
		return nil, errors.New("Retriever called on a nil Retriever; check that all retrievers are defined")
	}
	return (*retrieverAction)(r).Run(ctx, req, nil)
}

// RetrieveOption configures params of the Retrieve call.
type RetrieveOption func(req *RetrieverRequest) error

// WithRetrieverText adds a simple text as document to RetrieveRequest.
func WithRetrieverText(text string) RetrieveOption {
	return func(req *RetrieverRequest) error {
		req.Document = DocumentFromText(text, nil)
		return nil
	}
}

// WithRetrieverDoc adds a document to RetrieveRequest.
func WithRetrieverDoc(doc *Document) RetrieveOption {
	return func(req *RetrieverRequest) error {
		req.Document = doc
		return nil
	}
}

// WithRetrieverOpts retriever options to RetrieveRequest.
func WithRetrieverOpts(opts any) RetrieveOption {
	return func(req *RetrieverRequest) error {
		req.Options = opts
		return nil
	}
}

// Retrieve calls the retrivers with provided options.
func Retrieve(ctx context.Context, r Retriever, opts ...RetrieveOption) (*RetrieverResponse, error) {
	req := &RetrieverRequest{}
	for _, with := range opts {
		err := with(req)
		if err != nil {
			return nil, err
		}
	}
	return r.Retrieve(ctx, req)
}

// IndexerOption configures params of the Index call.
type IndexerOption func(req *IndexerRequest) error

// WithIndexerDoc adds a document to IndexRequest.
func WithIndexerDocs(docs ...*Document) IndexerOption {
	return func(req *IndexerRequest) error {
		req.Documents = docs
		return nil
	}
}

// WithIndexerOpts sets indexer options on IndexRequest.
func WithIndexerOpts(opts any) IndexerOption {
	return func(req *IndexerRequest) error {
		req.Options = opts
		return nil
	}
}

// Index calls the indexer with provided options.
func Index(ctx context.Context, r Indexer, opts ...IndexerOption) error {
	req := &IndexerRequest{}
	for _, with := range opts {
		err := with(req)
		if err != nil {
			return err
		}
	}
	return r.Index(ctx, req)
}

func (i *indexerActionDef) Name() string { return (*indexerAction)(i).Name() }

func (r *retrieverActionDef) Name() string { return (*retrieverAction)(r).Name() }
