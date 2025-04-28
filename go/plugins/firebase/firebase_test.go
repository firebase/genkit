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

	firebasev4 "firebase.google.com/go/v4"
	"github.com/firebase/genkit/go/genkit"
)

/*
  - Pre-requisites to run this test:

Same as that in retriever_test.go
*/
func TestInit(t *testing.T) {
	t.Parallel()

	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		t.Fatal(err)
	}

	firebaseApp, _ := firebasev4.NewApp(ctx, nil)

	tests := []struct {
		name          string
		expectedError string
		projectId     string
		app           *firebasev4.App
	}{
		{
			name:          "Successful initialization with project id",
			expectedError: "",
			projectId:     "test-app",
			app:           nil,
		},
		{
			name:          "Successful initialization with app",
			expectedError: "",
			projectId:     "",
			app:           firebaseApp,
		},
		{
			name:          "Initialise Plugin without app and project-id",
			expectedError: "firebase.Init: provide ProjectId or App", // Expecting an error when no app/projectId is passed
			projectId:     "",
			app:           nil,
		},
		{
			name:          "Initialise Plugin with both app and project-id",
			expectedError: "firebase.Init: provide either ProjectId or App, not both", // Expecting an error when no app/projectId is passed
			projectId:     "test-app",
			app:           firebaseApp,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := &Firebase{
				ProjectId: tt.projectId,
				App:       tt.app,
			}
			err = f.Init(ctx, g)

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
