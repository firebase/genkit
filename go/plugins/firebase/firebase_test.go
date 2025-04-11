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

	"github.com/firebase/genkit/go/genkit"
)

/*
  - Pre-requisites to run this test:

Same as that in retriever_test.go
*/
func TestInit(t *testing.T) {
	t.Parallel()
	f := &Firebase{
		ProjectId: "test-id",
	}
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name          string
		expectedError string
	}{

		{
			name:          "Successful initialization",
			expectedError: "",
		},
		{
			name:          "Reinitialise Plugin",
			expectedError: "firebase.Init: plugin already initialized", // Expecting an error when no app is passed

		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {

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
