// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package snippets

import (
	"context"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/vertexai"
)

func vertexaiEx(ctx context.Context) error {
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// [START init]
	if err := (&vertexai.VertexAI{}).Init(ctx, g); err != nil {
		return err
	}
	// [END init]

	yourProjectID := ""
	// [START initproj]
	if err := (&vertexai.VertexAI{ProjectID: yourProjectID}).Init(ctx, g); err != nil {
		return err
	}
	// [END initproj]

	// [START initloc]
	if err := (&vertexai.VertexAI{Location: "asia-south1"}).Init(ctx, g); err != nil {
		return err
	}
	// [END initloc]

	// [START model]
	langModel := vertexai.Model(g, "gemini-1.5-flash")
	// [END model]

	// [START gen]
	genRes, err := genkit.GenerateText(ctx, g,
		ai.WithModel(langModel),
		ai.WithPromptText("Tell me a joke."))
	if err != nil {
		return err
	}
	// [END gen]

	_ = genRes

	var userInput string

	// [START embedder]
	embeddingModel := vertexai.Embedder(g, "text-embedding-004")
	// [END embedder]

	// [START embed]
	embedRes, err := ai.Embed(ctx, embeddingModel, ai.WithEmbedText(userInput))
	if err != nil {
		return err
	}
	// [END embed]

	_ = embedRes

	var myRetriever ai.Retriever

	// [START retrieve]
	retrieveRes, err := ai.Retrieve(ctx, myRetriever, ai.WithRetrieverText(userInput))
	if err != nil {
		return err
	}
	// [END retrieve]

	_ = retrieveRes

	var myIndexer ai.Indexer
	var docsToIndex []*ai.Document

	// [START index]
	if err := ai.Index(ctx, myIndexer, ai.WithIndexerDocs(docsToIndex...)); err != nil {
		return err
	}
	// [END index]

	return nil
}
