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

package firebase

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"sync"

	firebasev4 "firebase.google.com/go/v4"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

// Firebase plugin for Genkit, providing integration with Firebase services.
// This plugin allows users to define retrievers and indexers for Firebase Firestore.
const provider = "firebase"                // Identifier for the Firebase plugin.
const projectIdEnv = "FIREBASE_PROJECT_ID" // Environment variable for the Firebase project ID.

// Firebase FireStore passes configuration options to the plugin.
type Firebase struct {
	ProjectId string          // Firebase project ID.
	App       *firebasev4.App // Firebase app instance.
	retriever ai.Retriever    // AI retriever instance.
	mu        sync.Mutex      // Mutex to control concurrent access.
	initted   bool            // Tracks whether the plugin has been initialized.
}

// Name returns the name of the plugin.
func (f *Firebase) Name() string {
	return provider
}

// Init initializes the Firebase plugin.
func (f *Firebase) Init(ctx context.Context, g *genkit.Genkit) error {
	f.mu.Lock()         // Lock to ensure thread-safe initialization.
	defer f.mu.Unlock() // Unlock when the function exits.

	// Resolve the Firebase project ID.
	projectId := resolveProjectId(f.ProjectId)

	// Check if the plugin is already initialized.
	if f.initted {
		return fmt.Errorf("firebase.Init: plugin already initialized")
	}

	if f.App == nil && f.ProjectId == "" {
		return fmt.Errorf("firebase.Init: provide projectId or firebase app")
	} else if f.App != nil && f.ProjectId != "" {
		return fmt.Errorf("firebase.Init: provide either projectId or firebase app not both")
	} else if f.App == nil && f.ProjectId != "" {
		// Configure and initialize the Firebase app.
		firebaseApp, err := firebasev4.NewApp(ctx, &firebasev4.Config{ProjectID: projectId})
		if err != nil {
			log.Fatalf("Error initializing Firebase App: %v", err) // Log and exit on failure.
		}
		f.App = firebaseApp
		f.ProjectId = projectId
	}

	f.initted = true // Mark the plugin as initialized.
	return nil
}

// DefineRetriever defines a Retriever with the given configuration.
func DefineRetriever(ctx context.Context, g *genkit.Genkit, cfg RetrieverOptions) (ai.Retriever, error) {
	// Lookup the Firebase plugin from the registry.
	f := genkit.LookupPlugin(g, provider).(*Firebase)
	if f == nil {
		return nil, errors.New("firebase plugin not found; did you call firebase.Init with the firebase plugin")
	}

	// Initialize Firestore client.
	firestoreClient, err := f.App.Firestore(ctx)
	if err != nil {
		log.Fatalf("Error creating Firestore client: %v", err) // Log and exit on failure.
	}

	// Define a Firestore retriever using the client.
	retriever, err := DefineFirestoreRetriever(g, cfg, firestoreClient)
	if err != nil {
		return nil, fmt.Errorf("DefineRetriever: failed to initialize retriever %s: %v", cfg.Name, err)
	}
	f.retriever = retriever // Cache the retriever instance.
	return retriever, nil
}

// resolveProjectId reads the projectId from the environment if necessary.
func resolveProjectId(projectId string) string {
	// Return the provided project ID if it's not empty.
	if projectId != "" {
		return projectId
	}

	// Otherwise, read the project ID from the environment variable.
	projectId = os.Getenv(projectIdEnv)
	return projectId
}
