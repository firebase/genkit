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

package googleai_test

import (
	"context"
	"flag"
	"testing"

	"github.com/google/genkit/go/genkit"
	"github.com/google/genkit/go/plugins/googleai"
)

// The tests here only work with an API key set to a valid value.
var apiKey = flag.String("key", "", "Gemini API key")

func TestEmbedder(t *testing.T) {
	if *apiKey == "" {
		t.Skipf("no -key provided")
	}
	ctx := context.Background()
	e, err := googleai.NewEmbedder(ctx, "embedding-001", *apiKey)
	if err != nil {
		t.Fatal(err)
	}
	out, err := e.Embed(ctx, &genkit.EmbedRequest{
		Document: &genkit.Document{Content: []*genkit.Part{genkit.NewTextPart("yellow banana")}},
	})
	if err != nil {
		t.Fatal(err)
	}

	// There's not a whole lot we can test about the result.
	// Just do a few sanity checks.
	if len(out) < 100 {
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

func TestTextGenerator(t *testing.T) {
	if *apiKey == "" {
		t.Skipf("no -key provided")
	}
	ctx := context.Background()
	a, err := googleai.NewGenerator(ctx, "gemini-1.0-pro", *apiKey)
	if err != nil {
		t.Fatal(err)
	}
	req := &genkit.GenerateRequest{
		Candidates: 1,
		Messages: []*genkit.Message{
			&genkit.Message{
				Content: []*genkit.Part{genkit.NewTextPart("Which country was Napoleon the emperor of?")},
				Role:    genkit.RoleUser,
			},
		},
	}

	resp, err := a.Run(ctx, req)
	if err != nil {
		t.Fatal(err)
	}
	out := resp.Candidates[0].Message.Content[0].Text()
	if out != "France" {
		t.Errorf("got \"%s\", expecting \"France\"", out)
	}
}
