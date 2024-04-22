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

package vertexai_test

import (
	"context"
	"flag"
	"strings"
	"testing"

	"github.com/google/genkit/go/ai"
	"github.com/google/genkit/go/plugins/vertexai"
)

// The tests here only work with a project set to a valid value.
// The user running these tests must be authenticated, for example by
// setting a valid GOOGLE_APPLICATION_CREDENTIALS environment variable.
var projectID = flag.String("projectid", "", "VertexAI project")
var location = flag.String("location", "us-central1", "geographic location")

func TestGenerator(t *testing.T) {
	if *projectID == "" {
		t.Skipf("no -projectid provided")
	}
	ctx := context.Background()
	g, err := vertexai.NewGenerator(ctx, "gemini-1.0-pro", *projectID, *location)
	if err != nil {
		t.Fatal(err)
	}
	req := &ai.GenerateRequest{
		Candidates: 1,
		Messages: []*ai.Message{
			&ai.Message{
				Content: []*ai.Part{ai.NewTextPart("Which country was Napoleon the emperor of?")},
				Role:    ai.RoleUser,
			},
		},
	}

	resp, err := g.Generate(ctx, req)
	if err != nil {
		t.Fatal(err)
	}
	out := resp.Candidates[0].Message.Content[0].Text()
	if !strings.Contains(out, "France") {
		t.Errorf("got \"%s\", expecting it would contain \"France\"", out)
	}
}
