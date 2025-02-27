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
	"testing"

	firebase "firebase.google.com/go/v4"
	"github.com/firebase/genkit/go/genkit"
)

func TestInit(t *testing.T) {
	t.Parallel()

	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name          string
		config        *FirebasePluginConfig
		expectedError string
		setup         func() error
	}{
		{
			name: "Successful initialization",
			config: &FirebasePluginConfig{
				App: &firebase.App{}, // Mock Firebase app
			},
			expectedError: "",
			setup: func() error {
				return nil // No setup required, first call should succeed
			},
		},
		{
			name: "Initialization when already initialized",
			config: &FirebasePluginConfig{
				App: &firebase.App{}, // Mock Firebase app
			},
			expectedError: "",
			setup: func() error {
				// Initialize once
				return Init(ctx, g, &FirebasePluginConfig{
					App: &firebase.App{}, // Mock Firebase app
				})
			},
		},
		{
			name: "Initialization with missing App",
			config: &FirebasePluginConfig{
				App: nil, // No app provided
			},
			expectedError: "firebase.Init: no Firebase app provided", // Expecting an error when no app is passed
			setup: func() error {
				return nil // No setup required
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			defer unInit()

			if err := tt.setup(); err != nil {
				t.Fatalf("Setup failed: %v", err)
			}

			err := Init(ctx, g, tt.config)

			if tt.expectedError != "" {
				if err == nil || err.Error() != tt.expectedError {
					t.Errorf("Expected error %q, got %v", tt.expectedError, err)
				}
			} else if err != nil {
				t.Errorf("Unexpected error: %v", err)
			}
		})
	}
}
