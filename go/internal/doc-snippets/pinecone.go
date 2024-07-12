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
	if err := pinecone.Init(ctx, ""); err != nil {
		return err
	}
	//!-init

	var pineconeAPIKey string
	//!+initkey
	if err := pinecone.Init(ctx, pineconeAPIKey); err != nil {
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
	if err := menuIndexer.Index(
		ctx,
		&ai.IndexerRequest{Documents: docChunks, Options: nil},
	); err != nil {
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
		Options:  nil,
	})
	if err != nil {
		return err
	}
	menuInfo := resp.Documents
	//!-retrieve

	_ = menuInfo

	return nil
}
