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
	"errors"
	"fmt"
	"sync"

	firebase "firebase.google.com/go/v4"
)

var state struct {
	mu      sync.Mutex
	initted bool
	app     *firebase.App
}

// FirebasePluginConfig is the configuration for the Firebase plugin.
type FirebasePluginConfig struct {
	AuthOverride     *map[string]interface{} `json:"databaseAuthVariableOverride"`
	DatabaseURL      string                  `json:"databaseURL"`
	ProjectID        string                  `json:"projectId"`
	ServiceAccountID string                  `json:"serviceAccountId"`
	StorageBucket    string                  `json:"storageBucket"`
}

// Init initializes the Firebase app with the provided configuration.
// If called more than once, it logs a message and returns nil.
func Init(ctx context.Context, cfg *FirebasePluginConfig) error {
	state.mu.Lock()
	defer state.mu.Unlock()

	if state.initted {
		// throw an error if the app is already initialized
		return errors.New("firebase.Init: Firebase app already initialized")
	}

	// Prepare the Firebase config
	firebaseConfig := &firebase.Config{
		AuthOverride:     cfg.AuthOverride,
		DatabaseURL:      cfg.DatabaseURL,
		ProjectID:        cfg.ProjectID, // Allow ProjectID to be empty
		ServiceAccountID: cfg.ServiceAccountID,
		StorageBucket:    cfg.StorageBucket,
	}

	// Initialize Firebase app with service account key if provided
	app, err := firebase.NewApp(ctx, firebaseConfig)
	if err != nil {
		errorStr := fmt.Sprintf("firebase.Init: %v", err)
		return errors.New(errorStr)
	}

	state.app = app
	state.initted = true

	return nil
}

// App returns a cached Firebase app.
// If the app is not initialized, it returns an error.
func App(ctx context.Context) (*firebase.App, error) {
	state.mu.Lock()
	defer state.mu.Unlock()

	if !state.initted {
		return nil, errors.New("firebase.App: Firebase app not initialized. Call Init first")
	}

	return state.app, nil
}
