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
	"errors"
	"fmt"
	"log"

	"cloud.google.com/go/firestore"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/firebase"
)

func main() {
	ctx := context.Background()

	// Firebase configuration
	firebaseConfig := &firebase.FirebasePluginConfig{
		ProjectID:        "your-project-id",
		DatabaseURL:      "https://your-project-id.firebaseio.com",
		ServiceAccountID: "your-service-account-id",
		StorageBucket:    "your-bucket.appspot.com",
	}

	// Initialize Firebase
	if err := firebase.Init(ctx, firebaseConfig); err != nil {
		log.Fatalf("Error initializing Firebase: %v", err)
	}

	// Initialize Firestore client
	app, err := firebase.App(ctx)
	if err != nil {
		log.Fatalf("Error getting Firebase app: %v", err)
	}
	firestoreClient, err := app.Firestore(ctx)
	if err != nil {
		log.Fatalf("Error creating Firestore client: %v", err)
	}
	defer firestoreClient.Close()

	// Firestore Retriever Configuration
	embedder := &MockEmbedder{}
	retrieverOptions := firebase.RetrieverOptions{
		Name:            "example-retriever",
		Client:          firestoreClient,
		Collection:      "documents",
		Embedder:        embedder,
		VectorField:     "embedding",
		ContentField:    "text",
		MetadataFields:  []string{"author", "date"},
		Limit:           10,
		DistanceMeasure: firestore.DistanceMeasureEuclidean,
		VectorType:      firebase.Vector64,
	}

	// Define Firestore Retriever
	retriever, err := firebase.DefineFirestoreRetriever(retrieverOptions)
	if err != nil {
		log.Fatalf("Error defining Firestore retriever: %v", err)
	}

	// Policy for Firebase Authentication
	policy := func(authContext genkit.AuthContext, input any) error {
		user := input.(string)
		if authContext == nil || authContext["UID"] != user {
			return errors.New("user ID does not match")
		}
		return nil
	}

	// Create Firebase Auth with required authentication
	firebaseAuth, err := firebase.NewAuth(ctx, policy, true)
	if err != nil {
		log.Fatalf("Error setting up Firebase auth: %v", err)
	}

	// Flow that requires authentication
	flowWithRequiredAuth := genkit.DefineFlow("flow-with-required-auth", func(ctx context.Context, user string) (string, error) {
		// Perform Firestore retrieval based on user input
		req := &ai.RetrieverRequest{
			Document: ai.DocumentFromText("Query for user: "+user, nil),
		}
		resp, err := retriever.Retrieve(ctx, req)
		if err != nil {
			return "", fmt.Errorf("retriever error: %w", err)
		}
		if len(resp.Documents) == 0 {
			return "", fmt.Errorf("no documents retrieved")
		}
		return fmt.Sprintf("Retrieved document: %s", resp.Documents[0].Content[0].Text), nil
	}, genkit.WithFlowAuth(firebaseAuth))

	// Flow that does not require authentication
	flowWithoutAuth := genkit.DefineFlow("flow-without-required-auth", func(ctx context.Context, user string) (string, error) {
		// Firestore retrieval for unauthenticated users
		req := &ai.RetrieverRequest{
			Document: ai.DocumentFromText("Query for user: "+user, nil),
		}
		resp, err := retriever.Retrieve(ctx, req)
		if err != nil {
			return "", fmt.Errorf("retriever error: %w", err)
		}
		if len(resp.Documents) == 0 {
			return "", fmt.Errorf("no documents retrieved")
		}
		return fmt.Sprintf("Retrieved document for unauthenticated user: %s", resp.Documents[0].Content[0].Text), nil
	}, genkit.WithFlowAuth(nil))

	// Define a super-caller flow that calls both flows
	genkit.DefineFlow("super-caller", func(ctx context.Context, _ struct{}) (string, error) {
		// Run flow with required auth
		resp1, err := flowWithRequiredAuth.Run(ctx, "admin-user", genkit.WithLocalAuth(map[string]any{"UID": "admin-user"}))
		if err != nil {
			return "", fmt.Errorf("flowWithRequiredAuth: %w", err)
		}

		// Run flow without required auth
		resp2, err := flowWithoutAuth.Run(ctx, "guest-user")
		if err != nil {
			return "", fmt.Errorf("flowWithoutAuth: %w", err)
		}

		return resp1 + ", " + resp2, nil
	})

	// Initialize Genkit
	if err := genkit.Init(ctx, nil); err != nil {
		log.Fatal(err)
	}
}

// MockEmbedder is used to simulate an AI embedder for testing purposes.
type MockEmbedder struct{}

func (e *MockEmbedder) Name() string {
	return "MockEmbedder"
}

func (e *MockEmbedder) Embed(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
	var embeddings []*ai.DocumentEmbedding
	for _, doc := range req.Documents {
		var embedding []float32
		switch doc.Content[0].Text {
		case "Query for user: admin-user":
			embedding = []float32{0.9, 0.1, 0.0}
		default:
			embedding = []float32{0.0, 0.0, 0.0}
		}
		embeddings = append(embeddings, &ai.DocumentEmbedding{Embedding: embedding})
	}
	return &ai.EmbedResponse{Embeddings: embeddings}, nil
}
