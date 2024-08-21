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

package ollama

import (
	"context"
	"flag"
	"testing"

	"github.com/firebase/genkit/go/ai"
)

var embedderName = flag.String("embedder-name", "nomic-embed-text", "embedder name")

func TestLiveEmbedding(t *testing.T) {
	if !*testLive {
		t.Skip("skipping go/plugins/ollama live test")
	}

	ctx := context.Background()

	// Initialize the Ollama plugin
	err := Init(ctx, &Config{
		ServerAddress: *serverAddress,
	})
	defer uninit()
	if err != nil {
		t.Fatal(err)
	}
	DefineEmbedder(*embedderName)

	// Define and use the embedder
	embedder := Embedder(*embedderName)
	if embedder == nil {
		t.Fatalf("failed to find embedder: %s", *embedderName)
	}

	t.Run("embedder", func(t *testing.T) {

		res, err := ai.Embed(ctx, embedder, ai.WithEmbedDocs(
			ai.DocumentFromText("time flies like an arrow", nil),
			ai.DocumentFromText("fruit flies like a banana", nil),
		))
		if err != nil {
			t.Fatal(err)
		}

		// Sanity checks on the embedding results
		for _, de := range res.Embeddings {
			out := de.Embedding
			if len(out) < 100 { // Assuming embeddings should have a length > 100
				t.Errorf("embedding vector looks too short: len(out)=%d", len(out))
			}
			var normSquared float32
			for _, x := range out {
				normSquared += x * x
			}
			if normSquared < 0.9 || normSquared > 1.1 {
				t.Errorf("embedding vector not unit length: %f", normSquared)
			}
		}
	})
}
