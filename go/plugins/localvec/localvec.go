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

// Package localvec is a local vector database for development and testing.
// The database is stored in a file in the local file system.
// Production code should use a real vector database.
package localvec

import (
	"cmp"
	"context"
	"crypto/md5"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"math"
	"os"
	"path/filepath"
	"slices"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/logger"
)

// Init register an action to be used with ai.
func Init(ctx context.Context, dir, name string, embedder ai.Embedder, embedderOptions any) error {
	r, err := New(ctx, dir, name, embedder, embedderOptions)
	if err != nil {
		return err
	}
	ai.RegisterRetriever("devLocalVectorStore/"+name, r)
	return nil
}

// New returns a new local vector database. This will register a new
// retriever with genkit, and also return it.
// This retriever may only be used by a single goroutine at a time.
// This is based on js/plugins/dev-local-vectorstore/src/index.ts.
func New(ctx context.Context, dir, name string, embedder ai.Embedder, embedderOptions any) (ai.Retriever, error) {
	r, err := newRetriever(ctx, dir, name, embedder, embedderOptions)
	if err != nil {
		return nil, err
	}
	return r, nil
}

// retriever implements the [ai.Retriever] interface
// for a local vector database.
type retriever struct {
	filename        string
	embedder        ai.Embedder
	embedderOptions any
	data            map[string]dbValue
}

// dbValue is the type of a document stored in the database.
type dbValue struct {
	Doc       *ai.Document `json:"doc"`
	Embedding []float32    `json:"embedding"`
}

// newRetriever returns a new ai.Retriever to register.
func newRetriever(ctx context.Context, dir, name string, embedder ai.Embedder, embedderOptions any) (ai.Retriever, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	dbname := "__db_" + name + ".json"
	filename := filepath.Join(dir, dbname)
	f, err := os.Open(filename)
	var data map[string]dbValue
	if err != nil {
		if !errors.Is(err, fs.ErrNotExist) {
			return nil, err
		}
	} else {
		defer f.Close()
		decoder := json.NewDecoder(f)
		if err := decoder.Decode(&data); err != nil {
			return nil, err
		}
	}

	r := &retriever{
		filename:        filename,
		embedder:        embedder,
		embedderOptions: embedderOptions,
		data:            data,
	}
	return r, nil
}

// Index implements the genkit [ai.Retriever.Index] method.
func (r *retriever) Index(ctx context.Context, req *ai.IndexerRequest) error {
	for _, doc := range req.Documents {
		ereq := &ai.EmbedRequest{
			Document: doc,
			Options:  r.embedderOptions,
		}
		vals, err := r.embedder.Embed(ctx, ereq)
		if err != nil {
			return fmt.Errorf("localvec index embedding failed: %v", err)
		}

		id, err := docID(doc)
		if err != nil {
			return err
		}

		if _, ok := r.data[id]; ok {
			logger.FromContext(ctx).Debug("localvec skipping document because already present", "id", id)
			continue
		}

		if r.data == nil {
			r.data = make(map[string]dbValue)
		}

		r.data[id] = dbValue{
			Doc:       doc,
			Embedding: vals,
		}
	}

	// Update the file every time we add documents.
	tmpname := r.filename + ".tmp"
	f, err := os.Create(tmpname)
	if err != nil {
		return err
	}
	encoder := json.NewEncoder(f)
	if err := encoder.Encode(r.data); err != nil {
		return err
	}
	if err := f.Close(); err != nil {
		return err
	}

	return nil
}

// RetrieverOptions may be passed in the Options field
// of [ai.RetrieverRequest] to pass options to the retriever.
// The Options field should be either nil or a value of type *RetrieverOptions.
type RetrieverOptions struct {
	K int `json:"k,omitempty"` // number of entries to return
}

// Retrieve implements the genkit [ai.Retriever.Retrieve] method.
func (r *retriever) Retrieve(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
	// Use the embedder to convert the document we want to
	// retrieve into a vector.
	ereq := &ai.EmbedRequest{
		Document: req.Document,
		Options:  r.embedderOptions,
	}
	vals, err := r.embedder.Embed(ctx, ereq)
	if err != nil {
		return nil, fmt.Errorf("localvec retrieve embedding failed: %v", err)
	}

	type scoredDoc struct {
		score float64
		doc   *ai.Document
	}
	scoredDocs := make([]scoredDoc, 0, len(r.data))
	for _, dbv := range r.data {
		score := similarity(vals, dbv.Embedding)
		scoredDocs = append(scoredDocs, scoredDoc{
			score: score,
			doc:   dbv.Doc,
		})
	}

	slices.SortFunc(scoredDocs, func(a, b scoredDoc) int {
		// We want to sort by descending score,
		// so pass b.score first to reverse the default ordering.
		return cmp.Compare(b.score, a.score)
	})

	k := 3
	if options, _ := req.Options.(*RetrieverOptions); options != nil {
		k = options.K
	}
	k = min(k, len(scoredDocs))

	docs := make([]*ai.Document, 0, k)
	for i := 0; i < k; i++ {
		docs = append(docs, scoredDocs[i].doc)
	}

	resp := &ai.RetrieverResponse{
		Documents: docs,
	}
	return resp, nil
}

// similarity computes the [cosine similarity] between two vectors.
//
// [cosine similarity]: https://en.wikipedia.org/wiki/Cosine_similarity
func similarity(vals1, vals2 []float32) float64 {
	l2norm := func(v float64, s, t float64) (float64, float64) {
		if v == 0 {
			return s, t
		}
		a := math.Abs(v)
		if a > t {
			r := t / v
			s = 1 + s*r*r
			t = a
		} else {
			r := v / t
			s = s + r*r
		}
		return s, t
	}

	dot := float64(0)
	s1 := float64(1)
	t1 := float64(0)
	s2 := float64(1)
	t2 := float64(0)

	for i, v1f := range vals1 {
		v1 := float64(v1f)
		v2 := float64(vals2[i])
		dot += v1 * v2
		s1, t1 = l2norm(v1, s1, t1)
		s2, t2 = l2norm(v2, s2, t2)
	}

	l1 := t1 * math.Sqrt(s1)
	l2 := t2 * math.Sqrt(s2)

	return dot / (l1 * l2)
}

// docID returns the ID to use for a Document.
// This is intended to be the same as the genkit Typescript computation.
func docID(doc *ai.Document) (string, error) {
	b, err := json.Marshal(doc)
	if err != nil {
		return "", fmt.Errorf("localvec: error marshaling document: %v", err)
	}
	return fmt.Sprintf("%02x", md5.Sum(b)), nil
}
