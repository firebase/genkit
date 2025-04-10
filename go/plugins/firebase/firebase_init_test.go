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
	"log"
	"testing"

	"cloud.google.com/go/firestore"
	firebasev4 "firebase.google.com/go/v4"
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
		name             string
		expectedError    string
		retrieverOptions RetrieverOptions
		useApp           bool
	}{
		{
			name: "Successful initialization",
			retrieverOptions: RetrieverOptions{
				Name:            "example-retriever1",
				Collection:      "test",
				Embedder:        nil,
				VectorField:     "embedding",
				ContentField:    "text",
				MetadataFields:  []string{"metadata"},
				Limit:           10,
				DistanceMeasure: firestore.DistanceMeasureEuclidean,
				VectorType:      Vector64,
			},
			expectedError: "",
			useApp:        true,
		},
		{
			name: "Initialization with missing App",
			retrieverOptions: RetrieverOptions{
				Name:            "example-retriever2",
				Collection:      "test",
				Embedder:        nil,
				VectorField:     "embedding",
				ContentField:    "text",
				MetadataFields:  []string{"metadata"},
				Limit:           10,
				DistanceMeasure: firestore.DistanceMeasureEuclidean,
				VectorType:      Vector64,
			},
			expectedError: "firebase.Init: no Firebase app provided", // Expecting an error when no app is passed
			useApp:        false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			conf := &firebasev4.Config{ProjectID: "test-app"}
			firebaseApp, err := firebasev4.NewApp(ctx, conf)
			if err != nil {
				log.Fatalf("Error initializing Firebase App: %v", err)
			}
			var f *Firebase
			if tt.useApp {
				f = &Firebase{
					App:           firebaseApp,
					RetrieverOpts: tt.retrieverOptions,
				}
			} else {
				f = &Firebase{
					RetrieverOpts: tt.retrieverOptions,
				}
			}

			defer f.UnInit()
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
