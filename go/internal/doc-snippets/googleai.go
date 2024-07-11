package snippets

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/googleai"
)

func googleaiEx(ctx context.Context) error {
	var err error

	//!+init
	err = googleai.Init(ctx, nil)
	if err != nil {
		return err
	}
	//!-init

	yourKey := ""
	//!+initkey
	err = googleai.Init(ctx, &googleai.Config{APIKey: yourKey})
	if err != nil {
		return err
	}
	//!-initkey

	//!+model
	langModel := googleai.Model("gemini-1.5-pro")
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
	embeddingModel := googleai.Embedder("text-embedding-004")
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
