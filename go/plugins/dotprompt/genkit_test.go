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

package dotprompt

import (
	"context"
	"fmt"
	"log"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

func testGenerate(ctx context.Context, req *ai.ModelRequest, cb func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	input := req.Messages[0].Content[0].Text
	output := fmt.Sprintf("AI reply to %q", input)

	r := &ai.ModelResponse{
		Message: &ai.Message{
			Content: []*ai.Part{
				ai.NewTextPart(output),
			},
		},
		Request: req,
	}
	return r, nil
}

func TestExecute(t *testing.T) {
	g, err := genkit.New(nil)
	if err != nil {
		log.Fatal(err)
	}
	testModel := ai.DefineModel(g.Reg, "test", "test", nil, testGenerate)
	t.Run("Model", func(t *testing.T) {
		p, err := New("TestExecute", "TestExecute", Config{Model: testModel})
		if err != nil {
			t.Fatal(err)
		}
		resp, err := p.Generate(context.Background(), g, &PromptRequest{}, nil)
		if err != nil {
			t.Fatal(err)
		}
		assertResponse(t, resp)
	})
	t.Run("ModelName", func(t *testing.T) {
		p, err := New("TestExecute", "TestExecute", Config{ModelName: "test/test"})
		if err != nil {
			t.Fatal(err)
		}
		resp, err := p.Generate(context.Background(), g, &PromptRequest{}, nil)
		if err != nil {
			t.Fatal(err)
		}
		assertResponse(t, resp)
	})
}

func assertResponse(t *testing.T, resp *ai.ModelResponse) {
	if resp.Message == nil {
		t.Fatal("response has candidate with no message")
	}
	if len(resp.Message.Content) != 1 {
		t.Errorf("got %d message parts, want 1", len(resp.Message.Content))
		if len(resp.Message.Content) < 1 {
			t.FailNow()
		}
	}
	got := resp.Message.Content[0].Text
	want := `AI reply to "TestExecute"`
	if got != want {
		t.Errorf("fake model replied with %q, want %q", got, want)
	}
}
