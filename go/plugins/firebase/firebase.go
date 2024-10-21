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

package firebase

import (
	"context"
	"fmt"
	"log"
	"sync"

	firebase "firebase.google.com/go/v4"
	"firebase.google.com/go/v4/auth"
	"github.com/firebase/genkit/go/ai"
)

var state struct {
	mu         sync.Mutex     // Ensures thread-safe access to state
	initted    bool           // Tracks if the plugin has been initialized
	app        *firebase.App  // Holds the Firebase app instance
	retrievers []ai.Retriever // Holds the list of initialized retrievers
}

// FirebaseApp is an interface to represent the Firebase App object
type FirebaseApp interface {
	Auth(ctx context.Context) (*auth.Client, error)
}

// FirebasePluginConfig is the configuration for the Firebase plugin.
// It passes an already initialized Firebase app and retriever options.
type FirebasePluginConfig struct {
	App        *firebase.App      // Pre-initialized Firebase app
	Retrievers []RetrieverOptions // Array of retriever options
}

// Init initializes the plugin with the provided configuration.
// It caches the provided Firebase app and initializes retrievers.
func Init(ctx context.Context, cfg *FirebasePluginConfig) error {
	state.mu.Lock()
	defer state.mu.Unlock()

	if state.initted {
		log.Println("firebase.Init: plugin already initialized, returning without reinitializing")
		return nil
	}

	// Ensure an app is provided
	if cfg.App == nil {
		return fmt.Errorf("firebase.Init: no Firebase app provided")
	}

	// Cache the provided app
	state.app = cfg.App

	// Initialize retrievers
	var retrievers []ai.Retriever
	for _, retrieverCfg := range cfg.Retrievers {
		retriever, err := DefineFirestoreRetriever(retrieverCfg)
		if err != nil {
			return fmt.Errorf("firebase.Init: failed to initialize retriever %s: %v", retrieverCfg.Name, err)
		}
		retrievers = append(retrievers, retriever)
	}

	// Cache the initialized retrievers
	state.retrievers = retrievers
	state.initted = true

	return nil
}

// unInit clears the initialized plugin state.
func unInit() {
	state.mu.Lock()
	defer state.mu.Unlock()

	state.initted = false
	state.app = nil
	state.retrievers = nil
}

// App returns the cached Firebase app.
// If the app is not initialized, it returns an error.
func App(ctx context.Context) (*firebase.App, error) {
	state.mu.Lock()
	defer state.mu.Unlock()

	if !state.initted {
		return nil, fmt.Errorf("firebase.App: Firebase app not initialized. Call Init first")
	}

	return state.app, nil
}

// Retrievers returns the cached list of retrievers.
// If retrievers are not initialized, it returns an error.
func Retrievers(ctx context.Context) ([]ai.Retriever, error) {
	state.mu.Lock()
	defer state.mu.Unlock()

	if !state.initted {
		return nil, fmt.Errorf("firebase.Retrievers: Plugin not initialized. Call Init first")
	}

	return state.retrievers, nil
}
