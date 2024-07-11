package snippets

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/vertexai"
)

func vertexaiEx(ctx context.Context) error {
	var err error

	//!+init
	err = vertexai.Init(ctx, nil)
	if err != nil {
		return err
	}
	//!-init

	yourProjectID := ""
	//!+initproj
	err = vertexai.Init(ctx, &vertexai.Config{ProjectID: yourProjectID})
	if err != nil {
		return err
	}
	//!-initproj

	//!+initloc
	err = vertexai.Init(ctx, &vertexai.Config{Location: "asia-south1"})
	if err != nil {
		return err
	}
	//!-initloc

	//!+model
	langModel := vertexai.Model("gemini-1.5-pro")
	//!-model

	//!+gen
	genRes, err := langModel.Generate(ctx, ai.NewGenerateRequest(
		nil, ai.NewUserTextMessage("Tell me a joke.")), nil)
	if err != nil {
		return err
	}
	//!-gen

	_ = genRes

	var userInput string

	//!+embedder
	embeddingModel := vertexai.Embedder("text-embedding-004")
	//!-embedder

	//!+embed
	embedRes, err := embeddingModel.Embed(ctx, &ai.EmbedRequest{
		Documents: []*ai.Document{ai.DocumentFromText(userInput, nil)},
	})
	if err != nil {
		return err
	}
	//!-embed

	_ = embedRes

	var myRetriever *ai.Retriever

	//!+retrieve
	retrieveRes, err := myRetriever.Retrieve(ctx, &ai.RetrieverRequest{
		Document: ai.DocumentFromText(userInput, nil),
	})
	if err != nil {
		return err
	}
	//!-retrieve

	_ = retrieveRes

	var myIndexer *ai.Indexer
	var docsToIndex []*ai.Document

	//!+index
	err = myIndexer.Index(ctx, &ai.IndexerRequest{Documents: docsToIndex})
	if err != nil {
		return err
	}
	//!-index

	return nil
}
