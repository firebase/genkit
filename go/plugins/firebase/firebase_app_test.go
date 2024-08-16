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
)

func TestApp(t *testing.T) {
	t.Parallel()

	ctx := context.Background()

	tests := []struct {
		name          string
		setup         func() error
		expectedError string
	}{
		{
			name: "Get App before initialization",
			setup: func() error {
				// No initialization setup here, calling App directly should fail
				return nil
			},
			expectedError: "firebase.App: Firebase app not initialized. Call Init first",
		},
		{
			name: "Get App after successful initialization",
			setup: func() error {
				// Properly initialize the app
				config := &FirebasePluginConfig{
					ProjectID: *firebaseProjectID,
				}
				return Init(ctx, config)
			},
			expectedError: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			defer UnInit()
			// Execute setup
			if err := tt.setup(); err != nil {
				t.Fatalf("Setup failed: %v", err)
			}

			// Now test the App function
			app, err := App(ctx)

			if tt.expectedError != "" {
				if err == nil || err.Error() != tt.expectedError {
					t.Errorf("Expected error %q, got %v", tt.expectedError, err)
				}
				if app != nil {
					t.Errorf("Expected no app, got %v", app)
				}
			} else if err != nil {
				t.Errorf("Unexpected error: %v", err)
			} else if app == nil {
				t.Errorf("Expected a valid app instance, got nil")
			}
		})
	}
}
