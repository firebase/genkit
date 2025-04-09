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
	"fmt"
	"log"
	"sync"

	firebasev4 "firebase.google.com/go/v4"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

// The provider used in the registry.
const provider = "firebase"

// FireStore passes configuration options to the plugin.
type FireStore struct {
	App           *firebasev4.App
	RetrieverOpts RetrieverOptions
	retriever     ai.Retriever
	mu            sync.Mutex // Mutex to control access.
	initted       bool       // Whether the plugin has been initialized.
}

// Name returns the name of the plugin.
func (f *FireStore) Name() string {
	return provider
}

// Init initializes the Firebase plugin..
func (f *FireStore) Init(ctx context.Context, g *genkit.Genkit) error {
	f.mu.Lock()
	defer f.mu.Unlock()

	if f.initted {
		log.Println("firebase.Init: plugin already initialized, returning without reinitializing")
		return nil
	}

	if f.App == nil {
		firebaseApp, err := firebasev4.NewApp(ctx, nil)
		if err != nil {
			log.Fatalf("Error initializing Firebase app: %v", err)
		}
		f.App = firebaseApp
	}

	retriever, err := DefineFirestoreRetriever(g, f.RetrieverOpts)
	if err != nil {
		return fmt.Errorf("firebase.Init: failed to initialize retriever %s: %v", f.RetrieverOpts.Name, err)
	}
	f.retriever = retriever
	f.initted = true
	return nil
}

// UnInit clears the initialized plugin state.
func (f *FireStore) UnInit() {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.initted = false
	f.App = nil
}

// Retriever returns retriever created in firestore object
func (f *FireStore) Retriever() (ai.Retriever, error) {
	f.mu.Lock()
	defer f.mu.Unlock()

	if !f.initted {
		return nil, fmt.Errorf("firebase.Retrievers: Plugin not initialized. Call Init first")
	}
	return f.retriever, nil
}
