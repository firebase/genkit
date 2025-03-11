// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"errors"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/registry"
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
	indexerActionDef   core.ActionDef[*IndexerRequest, struct{}, struct{}]
	retrieverActionDef core.ActionDef[*RetrieverRequest, *RetrieverResponse, struct{}]

	indexerAction   = core.ActionDef[*IndexerRequest, struct{}, struct{}]
	retrieverAction = core.ActionDef[*RetrieverRequest, *RetrieverResponse, struct{}]
)

// IndexerRequest is the data we pass to add documents to the database.
// The Options field is specific to the actual retriever implementation.
type IndexerRequest struct {
	Documents []*Document `json:"documents"`
	Options   any         `json:"options,omitempty"`
}

// RetrieverRequest is the data we pass to retrieve documents from the database.
// The Options field is specific to the actual retriever implementation.
type RetrieverRequest struct {
	Query   *Document `json:"query"`
	Options any       `json:"options,omitempty"`
}

// RetrieverResponse is the response to a document lookup.
type RetrieverResponse struct {
	Documents []*Document `json:"documents"`
}

// DefineIndexer registers the given index function as an action, and returns an
// [Indexer] that runs it.
func DefineIndexer(r *registry.Registry, provider, name string, index func(context.Context, *IndexerRequest) error) Indexer {
	f := func(ctx context.Context, req *IndexerRequest) (struct{}, error) {
		return struct{}{}, index(ctx, req)
	}
	return (*indexerActionDef)(core.DefineAction(r, provider, name, atype.Indexer, nil, f))
}

// IsDefinedIndexer reports whether an [Indexer] is defined.
func IsDefinedIndexer(r *registry.Registry, provider, name string) bool {
	return (*indexerActionDef)(core.LookupActionFor[*IndexerRequest, struct{}, struct{}](r, atype.Indexer, provider, name)) != nil
}

// LookupIndexer looks up an [Indexer] registered by [DefineIndexer].
// It returns nil if the model was not defined.
func LookupIndexer(r *registry.Registry, provider, name string) Indexer {
	return (*indexerActionDef)(core.LookupActionFor[*IndexerRequest, struct{}, struct{}](r, atype.Indexer, provider, name))
}

// DefineRetriever registers the given retrieve function as an action, and returns a
// [Retriever] that runs it.
func DefineRetriever(r *registry.Registry, provider, name string, ret func(context.Context, *RetrieverRequest) (*RetrieverResponse, error)) *retrieverActionDef {
	return (*retrieverActionDef)(core.DefineAction(r, provider, name, atype.Retriever, nil, ret))
}

// IsDefinedRetriever reports whether a [Retriever] is defined.
func IsDefinedRetriever(r *registry.Registry, provider, name string) bool {
	return (*retrieverActionDef)(core.LookupActionFor[*RetrieverRequest, *RetrieverResponse, struct{}](r, atype.Retriever, provider, name)) != nil
}

// LookupRetriever looks up a [Retriever] registered by [DefineRetriever].
// It returns nil if the model was not defined.
func LookupRetriever(r *registry.Registry, provider, name string) Retriever {
	return (*retrieverActionDef)(core.LookupActionFor[*RetrieverRequest, *RetrieverResponse, struct{}](r, atype.Retriever, provider, name))
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
		req.Query = DocumentFromText(text, nil)
		return nil
	}
}

// WithRetrieverDoc adds a document to RetrieveRequest.
func WithRetrieverDoc(doc *Document) RetrieveOption {
	return func(req *RetrieverRequest) error {
		req.Query = doc
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

// Index calls the retrivers with provided options.
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
