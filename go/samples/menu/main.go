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

package main

import (
	"context"
	"log"
	"os"

	"cloud.google.com/go/firestore"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/vertexai/vectorsearch"
)

// menuItem is the data model for an item on the menu.
type menuItem struct {
	Title       string  `json:"title" jsonschema_description:"The name of the menu item"`
	Description string  `json:"description" jsonschema_description:"Details including ingredients and preparation"`
	Price       float64 `json:"price" jsonschema_description:"Price in dollars"`
}

// menuQuestionInput is a question about the menu.
type menuQuestionInput struct {
	Question string `json:"question"`
}

// answerOutput is an answer to a question.
type answerOutput struct {
	Answer string `json:"answer"`
}

// dataMenuQuestionInput is a question about the menu,
// where the menu is provided in the JSON data.
type dataMenuQuestionInput struct {
	MenuData []*menuItem `json:"menuData"`
	Question string      `json:"question"`
}

// textMenuQuestionInput is for a question about the menu,
// where the menu is provided as unstructured text.
type textMenuQuestionInput struct {
	MenuText string `json:"menuText"`
	Question string `json:"question"`
}

func main() {
	ctx := context.Background()
	os.Setenv("GOOGLE_CLOUD_PROJECT", "drutuja-vvdaqs") // Set your Google Cloud project ID
	os.Setenv("GOOGLE_CLOUD_LOCATION", "us-central1")   // Set your Google Cloud location
	g, err := genkit.Init(ctx,
		genkit.WithPlugins(&googlegenai.VertexAI{}, &vectorsearch.Vectorsearch{}))

	if err != nil {
		log.Fatalf("failed to create Genkit: %v", err)
	}

	model := googlegenai.VertexAIModel(g, "gemini-2.0-flash")

	// bqClient, err := bigquery.NewClient(ctx, "drutuja-vvdaqs") // Replace with your Google Cloud project ID
	// if err != nil {
	// 	log.Fatalf("failed to create BigQuery client: %v", err)
	// }

	// Create the BigQuery Document Indexer.
	// datasetID := "vectorsearch_docs"  // Replace with your BigQuery dataset ID.
	// tableID := "vectorsearch_example" // Replace with your BigQuery table ID.
	// documentIndexer := vectorsearch.GetBigQueryDocumentIndexer(bqClient, datasetID, tableID)
	// documentRetriever := vectorsearch.GetBigQueryDocumentRetriever(bqClient, datasetID, tableID)

	collectionName := "genkit-vectorsearch-docs"
	databaseId := "genkit-vectorsearch-docs"                                                   // Replace with your Firestore collection name
	firestoreClient, err := firestore.NewClientWithDatabase(ctx, "drutuja-vvdaqs", databaseId) // Replace with your Google Cloud project ID
	documentIndexer := vectorsearch.GetFirestoreDocumentIndexer(firestoreClient, collectionName)
	documentRetriever := vectorsearch.GetFirestoreDocumentRetriever(firestoreClient, collectionName)

	// embedder := googlegenai.VertexAIEmbedder(g, "text-embedding-004")

	// if err := setup01(g, model); err != nil {
	// 	log.Fatal(err)
	// }
	// if err := setup02(g, model); err != nil {
	// 	log.Fatal(err)
	// }
	// if err := setup03(g, model); err != nil {
	// 	log.Fatal(err)
	// }

	// genkit.WithPlugins(&vectorsearch.Vectorsearch{
	// 	ProjectID: "drutuja-vvdaqs", // Replace with your Google Cloud project ID
	// 	Location:  "us-central1",    // Replace with your desired location
	// }

	// if err := v.Init(ctx, g); err != nil {
	// 	log.Fatalf("failed to initialize vectorsearch: %v", err)
	// }
	retriever, err := vectorsearch.DefineRetriever(ctx, g, vectorsearch.Config{
		IndexID: "4884595799557668864", // Replace with your index ID
	})
	if err != nil {
		log.Fatal(err)
	}
	if err := setup04(ctx, g, retriever, model, documentIndexer, documentRetriever); err != nil {
		log.Fatal(err)
	}

	// if err := setup05(g, model); err != nil {
	// 	log.Fatal(err)
	// }

	// <-ctx.Done()
}
