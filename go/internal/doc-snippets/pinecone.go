// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package snippets

import (
	"context"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googleai"
	"github.com/firebase/genkit/go/plugins/pinecone"
)

func pineconeEx(ctx context.Context) error {
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// [START init]
	if err := pinecone.Init(ctx, ""); err != nil {
		return err
	}
	// [END init]

	var pineconeAPIKey string
	// [START initkey]
	if err := pinecone.Init(ctx, pineconeAPIKey); err != nil {
		return err
	}
	// [END initkey]

	// [START defineindex]
	menuIndexer, err := pinecone.DefineIndexer(ctx, g, pinecone.Config{
		IndexID:  "menu_data",                                // Your Pinecone index
		Embedder: googleai.Embedder(g, "text-embedding-004"), // Embedding model of your choice
	})
	if err != nil {
		return err
	}
	// [END defineindex]

	var docChunks []*ai.Document

	// [START index]
	if err := ai.Index(
		ctx,
		menuIndexer,
		ai.WithIndexerDocs(docChunks...)); err != nil {
		return err
	}
	// [END index]

	// [START defineretriever]
	menuRetriever, err := pinecone.DefineRetriever(ctx, g, pinecone.Config{
		IndexID:  "menu_data",                                // Your Pinecone index
		Embedder: googleai.Embedder(g, "text-embedding-004"), // Embedding model of your choice
	})
	if err != nil {
		return err
	}
	// [END defineretriever]

	var userInput string

	// [START retrieve]
	resp, err := menuRetriever.Retrieve(ctx, &ai.RetrieverRequest{
		Query:   ai.DocumentFromText(userInput, nil),
		Options: nil,
	})
	if err != nil {
		return err
	}
	menuInfo := resp.Documents
	// [END retrieve]

	_ = menuInfo

	return nil
}
