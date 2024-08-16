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
	"flag"
	"testing"
)

// Define the flag with a default value of "demo-test"
var firebaseProjectID = flag.String("firebase-project-id", "demo-test", "Firebase project ID")

func TestInit(t *testing.T) {
	t.Parallel()

	ctx := context.Background()

	tests := []struct {
		name          string
		config        *FirebasePluginConfig
		expectedError string
		setup         func() error
	}{
		{
			name: "Successful initialization",
			config: &FirebasePluginConfig{
				ProjectID: *firebaseProjectID,
			},
			expectedError: "",
			setup: func() error {
				return nil // No setup required, first call should succeed
			},
		},
		{
			name: "Initialization when already initialized",
			config: &FirebasePluginConfig{
				ProjectID: *firebaseProjectID,
			},
			expectedError: "",
			setup: func() error {
				return Init(ctx, &FirebasePluginConfig{ProjectID: *firebaseProjectID}) // Initialize once
			},
		},
		{
			name: "Initialization with missing ProjectID",
			config: &FirebasePluginConfig{
				ProjectID: "",
			},
			expectedError: "", // No error expected, as ProjectID can be inferred
			setup: func() error {
				return nil // No setup required
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			defer UnInit()

			if err := tt.setup(); err != nil {
				t.Fatalf("Setup failed: %v", err)
			}

			err := Init(ctx, tt.config)

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
