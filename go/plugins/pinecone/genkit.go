// Copyright 2025 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package pinecone

import (
	"context"
	"crypto/md5"
	"encoding/json"
	"errors"
	"fmt"
	"maps"
	"slices"
	"strings"
	"sync"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

const provider = "pinecone"

// defaultTextKey is the default metadata key we use to store the
// document text as metadata of the documented stored in pinecone.
// This lets us map back from the document returned by a query to
// the text. In other words, rather than remembering the mapping
// between documents and pinecone data ourselves, we just store the
// documents in pinecone.
const defaultTextKey = "_content"

type Pinecone struct {
	APIKey string // API key to use for Pinecone requests.

	client  *client    // Client for the Pinecone service.
	mu      sync.Mutex // Mutex to control access.
	initted bool       // Whether the plugin has been initialized.
}

// Init initializes the Pinecone plugin.
// If apiKey is the empty string, it is read from the PINECONE_API_KEY
// environment variable.
func (p *Pinecone) Init(ctx context.Context, g *genkit.Genkit) (err error) {
	// Init initializes the Pinecone plugin.
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.initted {
		panic("pinecone.Init already called")
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("pinecone.Init: %w", err)
		}
	}()

	client, err := newClient(ctx, p.APIKey)
	if err != nil {
		return err
	}
	p.client = client
	p.initted = true
	return nil
}

// Config provides configuration options for [DefineIndexer] and [DefineRetriever].
type Config struct {
	IndexID         string      // The index ID to use.
	Embedder        ai.Embedder // Embedder to use. Required.
	EmbedderOptions any         // Options to pass to the embedder.
	TextKey         string      // Metadata key to use to store document text in Pinecone; the default is "_content".
}

// DefineIndexer defines an Indexer with the given configuration.
func DefineIndexer(ctx context.Context, g *genkit.Genkit, cfg Config) (ai.Indexer, error) {
	p := genkit.LookupPlugin(g, provider).(*Pinecone)
	if p == nil {
		return nil, errors.New("pinecone plugin not found; did you call genkit.Init with the pinecone plugin?")
	}

	ds, err := p.newDocStore(ctx, cfg)
	if err != nil {
		return nil, err
	}
	return genkit.DefineIndexer(g, provider, cfg.IndexID, ds.Index), nil
}

// DefineRetriever defines a Retriever with the given configuration.
func DefineRetriever(ctx context.Context, g *genkit.Genkit, cfg Config) (ai.Retriever, error) {
	p := genkit.LookupPlugin(g, provider).(*Pinecone)
	if p == nil {
		return nil, errors.New("pinecone plugin not found; did you call genkit.Init with the pinecone plugin?")
	}

	ds, err := p.newDocStore(ctx, cfg)
	if err != nil {
		return nil, err
	}
	return genkit.DefineRetriever(g, provider, cfg.IndexID, ds.Retrieve), nil
}

// IsDefinedIndexer reports whether the named [Indexer] is defined by this plugin.
func IsDefinedIndexer(g *genkit.Genkit, name string) bool {
	return genkit.LookupIndexer(g, provider, name) != nil
}

// IsDefinedRetriever reports whether the named [Retriever] is defined by this plugin.
func IsDefinedRetriever(g *genkit.Genkit, name string) bool {
	return genkit.LookupRetriever(g, provider, name) != nil
}

func (p *Pinecone) newDocStore(ctx context.Context, cfg Config) (*docStore, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if !p.initted {
		panic("pinecone.Init not called")
	}
	if cfg.IndexID == "" {
		return nil, errors.New("IndexID required")
	}
	if cfg.Embedder == nil {
		return nil, errors.New("Embedder required")
	}
	// TODO: cache these calls so we don't make them twice for the indexer and retriever.
	indexData, err := p.client.indexData(ctx, cfg.IndexID)
	if err != nil {
		return nil, err
	}
	index, err := p.client.index(ctx, indexData.Host)
	if err != nil {
		return nil, err
	}
	if cfg.TextKey == "" {
		cfg.TextKey = defaultTextKey
	}
	return &docStore{
		index:           index,
		embedder:        cfg.Embedder,
		embedderOptions: cfg.EmbedderOptions,
		textKey:         cfg.TextKey,
	}, nil
}

// Indexer returns the indexer with the given index name.
func Indexer(g *genkit.Genkit, name string) ai.Indexer {
	return genkit.LookupIndexer(g, provider, name)
}

// Retriever returns the retriever with the given index name.
func Retriever(g *genkit.Genkit, name string) ai.Retriever {
	return genkit.LookupRetriever(g, provider, name)
}

// IndexerOptions may be passed in the Options field
// of [ai.IndexerRequest] to pass options to Pinecone.
// The Options field should be either nil or a value of type *IndexerOptions.
type IndexerOptions struct {
	Namespace string `json:"namespace,omitempty"` // Pinecone namespace to use
}

// RetrieverOptions may be passed in the Options field
// of [ai.RetrieverRequest] to pass options to Pinecone.
// The Options field should be either nil or a value of type *RetrieverOptions.
type RetrieverOptions struct {
	Namespace string `json:"namespace,omitempty"` // Pinecone namespace to use
	Count     int    `json:"count,omitempty"`     // maximum number of values to retrieve
}

// docStore implements the genkit [ai.DocumentStore] interface.
type docStore struct {
	index           *index
	embedder        ai.Embedder
	embedderOptions any
	textKey         string
}

// Index implements the genkit Retriever.Index method.
func (ds *docStore) Index(ctx context.Context, req *ai.IndexerRequest) error {
	if len(req.Documents) == 0 {
		return nil
	}

	namespace := ""
	if req.Options != nil {
		// TODO: This is plausible when called directly
		// from Go code, but what will it look like when
		// run from a resumed flow?
		options, ok := req.Options.(*IndexerOptions)
		if !ok {
			return fmt.Errorf("pinecone.Index options have type %T, want %T", req.Options, &IndexerOptions{})
		}
		namespace = options.Namespace
	}

	// Use the embedder to convert each Document into a vector.
	vecs := make([]vector, 0, len(req.Documents))
	ereq := &ai.EmbedRequest{
		Input:   req.Documents,
		Options: ds.embedderOptions,
	}
	eres, err := ds.embedder.Embed(ctx, ereq)
	if err != nil {
		return fmt.Errorf("pinecone index embedding failed: %v", err)
	}
	for i, de := range eres.Embeddings {
		doc := req.Documents[i]
		id, err := docID(doc)
		if err != nil {
			return err
		}

		var metadata map[string]any
		if doc.Metadata == nil {
			metadata = make(map[string]any)
		} else {
			metadata = maps.Clone(doc.Metadata)
		}
		// TODO: This seems to be what the TypeScript code does,
		// but it loses the structure of the document.
		var sb strings.Builder
		for _, p := range doc.Content {
			sb.WriteString(p.Text)
		}
		metadata[ds.textKey] = sb.String()

		v := vector{
			ID:       id,
			Values:   de.Embedding,
			Metadata: metadata,
		}
		vecs = append(vecs, v)
	}

	if err := ds.index.upsert(ctx, vecs, namespace); err != nil {
		return err
	}

	// Pinecone is only eventually consistent.
	// Wait until the vectors are visible.
	wait := func() (bool, error) {
		delay := 10 * time.Millisecond
		for i := 0; i < 20; i++ {
			vec, err := ds.index.queryByID(ctx, vecs[0].ID, wantValues, namespace)
			if err != nil {
				return false, err
			}
			if vec != nil {
				// For some reason Pinecone doesn't
				// reliably return a vector with the
				// same ID.
				for _, v := range vecs {
					if vec.ID == v.ID && slices.Equal(vec.Values, v.Values) {
						return true, nil
					}
				}
			}
			time.Sleep(delay)
			delay *= 2
		}
		return false, nil
	}
	seen, err := wait()
	if err != nil {
		return err
	}
	if !seen {
		return errors.New("inserted Pinecone records never became visible")
	}

	return nil
}

// Retrieve implements the genkit Retriever.Retrieve method.
func (ds *docStore) Retrieve(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
	var (
		namespace string
		count     int
	)
	if req.Options != nil {
		// TODO: This is plausible when called directly
		// from Go code, but what will it look like when
		// run from a resumed flow?
		ropt, ok := req.Options.(*RetrieverOptions)
		if !ok {
			return nil, fmt.Errorf("pinecone.Retrieve options have type %T, want %T", req.Options, &RetrieverOptions{})
		}
		namespace = ropt.Namespace
		count = ropt.Count
	}

	// Use the embedder to convert the document we want to
	// retrieve into a vector.
	ereq := &ai.EmbedRequest{
		Input:   []*ai.Document{req.Query},
		Options: ds.embedderOptions,
	}
	eres, err := ds.embedder.Embed(ctx, ereq)
	if err != nil {
		return nil, fmt.Errorf("pinecone retrieve embedding failed: %v", err)
	}

	results, err := ds.index.query(ctx, eres.Embeddings[0].Embedding, count, wantMetadata, namespace)
	if err != nil {
		return nil, err
	}

	var docs []*ai.Document
	for _, result := range results {
		text, _ := result.Metadata[ds.textKey].(string)
		if text == "" {
			return nil, errors.New("Pinecone retrieve failed to fetch original document text")
		}
		delete(result.Metadata, ds.textKey)
		// TODO: This is what the TypeScript code does,
		// but it loses information for multimedia documents.
		d := ai.DocumentFromText(text, result.Metadata)
		docs = append(docs, d)
	}

	ret := &ai.RetrieverResponse{
		Documents: docs,
	}
	return ret, nil
}

// docID returns the ID to use for a Document.
// This is intended to be the same as the genkit Typescript computation.
func docID(doc *ai.Document) (string, error) {
	b, err := json.Marshal(doc)
	if err != nil {
		return "", fmt.Errorf("pinecone: error marshaling document: %v", err)
	}
	return fmt.Sprintf("%02x", md5.Sum(b)), nil
}
