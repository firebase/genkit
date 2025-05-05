package main

import (
	"context"
	"crypto/md5"
	"encoding/json"
	"fmt"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/plugins/localvec"
)

func Index(ctx context.Context, docs []*ai.Document, ds *localvec.DocStore) error {
	ereq := &ai.EmbedRequest{
		Input:   docs,
		Options: ds.EmbedderOptions(),
	}
	eres, err := ds.Embedder().Embed(ctx, ereq)
	if err != nil {
		return fmt.Errorf("localvec index embedding failed: %v", err)
	}
	for i, de := range eres.Embeddings {
		id, err := docID(docs[i])
		if err != nil {
			return err
		}
		if _, ok := ds.GetDbValue(id); ok {
			logger.FromContext(ctx).Debug("localvec skipping document because already present", "id", id)
			continue
		}

		ds.SetData(id, localvec.DbValue{
			Doc:       docs[i],
			Embedding: de.Embedding,
		})
	}

	// Update the file every time we add documents.
	// We use a temporary file to avoid losing the original
	// file, in case of a crash.
	tmpname := ds.FileName() + ".tmp"
	f, err := os.Create(tmpname)
	if err != nil {
		return err
	}
	encoder := json.NewEncoder(f)
	if err := encoder.Encode(ds.Data()); err != nil {
		return err
	}
	if err := f.Close(); err != nil {
		return err
	}
	if err := os.Rename(tmpname, ds.FileName()); err != nil {
		return err
	}

	return nil
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
