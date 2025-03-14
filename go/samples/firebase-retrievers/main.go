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

package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"cloud.google.com/go/firestore"
	firebasev4 "firebase.google.com/go/v4"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/firebase"
	"google.golang.org/api/option"
)

func main() {
	ctx := context.Background()

	// Load project ID and Firestore collection from environment variables
	projectID := os.Getenv("FIREBASE_PROJECT_ID")
	if projectID == "" {
		log.Fatal("Environment variable FIREBASE_PROJECT_ID is not set")
	}

	collectionName := os.Getenv("FIRESTORE_COLLECTION")
	if collectionName == "" {
		log.Fatal("Environment variable FIRESTORE_COLLECTION is not set")
	}

	// Initialize Firestore client
	firestoreClient, err := firestore.NewClient(ctx, projectID, option.WithCredentialsFile(""))
	if err != nil {
		log.Fatalf("Error creating Firestore client: %v", err)
	}
	defer firestoreClient.Close()

	// Firebase app configuration and initialization
	firebaseApp, err := firebasev4.NewApp(ctx, nil)
	if err != nil {
		log.Fatalf("Error initializing Firebase app: %v", err)
	}

	// Firebase configuration using the initialized app
	firebaseConfig := &firebase.FirebasePluginConfig{
		App: firebaseApp, // Pass the pre-initialized Firebase app
	}

	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// Initialize Firebase plugin
	if err := firebase.Init(ctx, g, firebaseConfig); err != nil {
		log.Fatalf("Error initializing Firebase: %v", err)
	}

	// Mock embedder
	embedder := &MockEmbedder{}

	// Famous films text
	films := []string{
		"The Godfather is a 1972 crime film directed by Francis Ford Coppola.",
		"The Dark Knight is a 2008 superhero film directed by Christopher Nolan.",
		"Pulp Fiction is a 1994 crime film directed by Quentin Tarantino.",
		"Schindler's List is a 1993 historical drama directed by Steven Spielberg.",
		"Inception is a 2010 sci-fi film directed by Christopher Nolan.",
		"The Matrix is a 1999 sci-fi film directed by the Wachowskis.",
		"Fight Club is a 1999 film directed by David Fincher.",
		"Forrest Gump is a 1994 drama directed by Robert Zemeckis.",
		"Star Wars is a 1977 sci-fi film directed by George Lucas.",
		"The Shawshank Redemption is a 1994 drama directed by Frank Darabont.",
	}

	// Define the index flow: Insert 10 documents about famous films
	genkit.DefineFlow(g, "flow-index-documents", func(ctx context.Context, _ struct{}) (string, error) {
		for i, filmText := range films {
			docID := fmt.Sprintf("doc-%d", i+1)
			embedding := []float64{float64(i+1) * 0.1, float64(i+1) * 0.2, float64(i+1) * 0.3}

			_, err := firestoreClient.Collection(collectionName).Doc(docID).Set(ctx, map[string]interface{}{
				"text":      filmText,
				"embedding": firestore.Vector64(embedding),
				"metadata":  fmt.Sprintf("metadata for doc %d", i+1),
			})
			if err != nil {
				return "", fmt.Errorf("failed to index document %d: %w", i+1, err)
			}
			log.Printf("Indexed document %d with text: %s", i+1, filmText)
		}
		return "10 film documents indexed successfully", nil
	})

	// Firestore Retriever Configuration
	retrieverOptions := firebase.RetrieverOptions{
		Name:            "example-retriever",
		Client:          firestoreClient,
		Collection:      collectionName,
		Embedder:        embedder,
		VectorField:     "embedding",
		ContentField:    "text",
		MetadataFields:  []string{"metadata"},
		Limit:           10,
		DistanceMeasure: firestore.DistanceMeasureEuclidean,
		VectorType:      firebase.Vector64,
	}

	// Define Firestore Retriever
	retriever, err := firebase.DefineFirestoreRetriever(g, retrieverOptions)
	if err != nil {
		log.Fatalf("Error defining Firestore retriever: %v", err)
	}

	// Define the retrieval flow: Retrieve documents based on user query
	genkit.DefineFlow(g, "flow-retrieve-documents", func(ctx context.Context, query string) (string, error) {
		// Perform Firestore retrieval based on user input
		req := &ai.RetrieverRequest{
			Query: ai.DocumentFromText(query, nil),
		}
		log.Println("Starting retrieval with query:", query)
		resp, err := retriever.Retrieve(ctx, req)
		if err != nil {
			return "", fmt.Errorf("retriever error: %w", err)
		}

		// Check if documents were retrieved
		if len(resp.Documents) == 0 {
			log.Println("No documents retrieved, response:", resp)
			return "", fmt.Errorf("no documents retrieved")
		}

		// Log the retrieved documents for debugging
		for _, doc := range resp.Documents {
			log.Printf("Retrieved document: %s", doc.Content[0].Text)
		}

		return fmt.Sprintf("Retrieved document: %s", resp.Documents[0].Content[0].Text), nil
	})

	<-ctx.Done()
}

// MockEmbedder is used to simulate an AI embedder for testing purposes.
type MockEmbedder struct{}

func (e *MockEmbedder) Name() string {
	return "MockEmbedder"
}

func (e *MockEmbedder) Embed(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
	var embeddings []*ai.DocumentEmbedding

	// Generate a simple uniform embedding for each document
	for _, doc := range req.Documents {
		// Example: Use the length of the document text to generate embeddings
		embedding := []float32{
			float32(len(doc.Content[0].Text)) * 0.1, // Scale based on text length
			0.5,                                     // Static value
			0.3,                                     // Static value
		}
		embeddings = append(embeddings, &ai.DocumentEmbedding{Embedding: embedding})
	}
	return &ai.EmbedResponse{Embeddings: embeddings}, nil
}
