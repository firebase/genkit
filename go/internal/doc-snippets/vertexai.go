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
	"github.com/firebase/genkit/go/plugins/vertexai"
)

func vertexaiEx(ctx context.Context) error {
	var err error

	// [START init]
	if err := vertexai.Init(ctx, nil); err != nil {
		return err
	}
	// [END init]

	yourProjectID := ""
	// [START initproj]
	if err := vertexai.Init(ctx, &vertexai.Config{ProjectID: yourProjectID}); err != nil {
		return err
	}
	// [END initproj]

	// [START initloc]
	if err := vertexai.Init(ctx, &vertexai.Config{Location: "asia-south1"}); err != nil {
		return err
	}
	// [END initloc]

	// [START model]
	langModel := vertexai.Model("gemini-1.5-pro")
	// [END model]

	// [START gen]
	genRes, err := langModel.Generate(ctx, ai.NewGenerateRequest(
		nil, ai.NewUserTextMessage("Tell me a joke.")), nil)
	if err != nil {
		return err
	}
	// [END gen]

	_ = genRes

	var userInput string

	// [START embedder]
	embeddingModel := vertexai.Embedder("text-embedding-004")
	// [END embedder]

	// [START embed]
	embedRes, err := embeddingModel.Embed(ctx, &ai.EmbedRequest{
		Documents: []*ai.Document{ai.DocumentFromText(userInput, nil)},
	})
	if err != nil {
		return err
	}
	// [END embed]

	_ = embedRes

	var myRetriever *ai.Retriever

	// [START retrieve]
	retrieveRes, err := myRetriever.Retrieve(ctx, &ai.RetrieverRequest{
		Document: ai.DocumentFromText(userInput, nil),
	})
	if err != nil {
		return err
	}
	// [END retrieve]

	_ = retrieveRes

	var myIndexer *ai.Indexer
	var docsToIndex []*ai.Document

	// [START index]
	if err := myIndexer.Index(ctx, &ai.IndexerRequest{Documents: docsToIndex}); err != nil {
		return err
	}
	// [END index]

	return nil
}
