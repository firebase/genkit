package snippets

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/googleai"
	"github.com/firebase/genkit/go/plugins/pinecone"
)

func pineconeEx(ctx context.Context) error {
	var err error

	//!+init
	err = pinecone.Init(ctx, "")
	if err != nil {
		return err
	}
	//!-init

	var pineconeAPIKey string
	//!+initkey
	err = pinecone.Init(ctx, pineconeAPIKey)
	if err != nil {
		return err
	}
	//!-initkey

	//!+defineindex
	menuIndexer, err := pinecone.DefineIndexer(ctx, pinecone.Config{
		IndexID:  "menu_data",                             // Your Pinecone index
		Embedder: googleai.Embedder("text-embedding-004"), // Embedding model of your choice
	})
	if err != nil {
		return err
	}
	//!-defineindex

	var docChunks []*ai.Document

	//!+index
	err = menuIndexer.Index(ctx, &ai.IndexerRequest{Documents: docChunks, Options: nil})
	if err != nil {
		return err
	}
	//!-index

	//!+defineretriever
	menuRetriever, err := pinecone.DefineRetriever(ctx, pinecone.Config{
		IndexID:  "menu_data",                             // Your Pinecone index
		Embedder: googleai.Embedder("text-embedding-004"), // Embedding model of your choice
	})
	if err != nil {
		return err
	}
	//!-defineretriever

	var userInput string

	//!+retrieve
	resp, err := menuRetriever.Retrieve(ctx, &ai.RetrieverRequest{
		Document: ai.DocumentFromText(userInput, nil),
		Options: nil,
	})
	if err != nil {
		return err
	}
	menuInfo := resp.Documents
	//!-retrieve

	_ = menuInfo

	return nil
}
