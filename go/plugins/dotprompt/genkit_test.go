// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package dotprompt

import (
	"context"
	"fmt"
	"log"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/google/go-cmp/cmp"
)

func testGenerate(ctx context.Context, req *ai.ModelRequest, cb func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	input := req.Messages[0].Content[0].Text
	output := fmt.Sprintf("AI reply to %q", input)

	if req.Output.Format == "json" {
		output = `{"text": "AI reply to JSON"}`
	}

	if cb != nil {
		cb(ctx, &ai.ModelResponseChunk{
			Content: []*ai.Part{ai.NewTextPart("stream!")},
		})
	}

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
	g, err := genkit.Init(context.Background())
	if err != nil {
		log.Fatal(err)
	}
	testModel := genkit.DefineModel(g, "test", "test", nil, testGenerate)
	t.Run("Model", func(t *testing.T) {
		p, err := New("TestExecute", "TestExecute", Config{Model: testModel})
		if err != nil {
			t.Fatal(err)
		}
		resp, err := p.Generate(context.Background(), g)
		if err != nil {
			t.Fatal(err)
		}
		assertResponse(t, resp, `AI reply to "TestExecute"`)
	})
	t.Run("ModelName", func(t *testing.T) {
		p, err := New("TestExecute", "TestExecute", Config{ModelName: "test/test"})
		if err != nil {
			t.Fatal(err)
		}
		resp, err := p.Generate(context.Background(), g)
		if err != nil {
			t.Fatal(err)
		}
		assertResponse(t, resp, `AI reply to "TestExecute"`)
	})
	t.Run("GenerateText", func(t *testing.T) {
		p, err := New("TestExecute", "TestExecute", Config{ModelName: "test/test"})
		if err != nil {
			t.Fatal(err)
		}
		resp, err := p.GenerateText(context.Background(), g)
		if err != nil {
			t.Fatal(err)
		}
		if resp != `AI reply to "TestExecute"` {
			t.Errorf("got %q, want %q", resp, `AI reply to "TestExecute"`)
		}
	})
	t.Run("GenerateData", func(t *testing.T) {
		p, err := New("TestExecute", "TestExecute", Config{ModelName: "test/test"})
		if err != nil {
			t.Fatal(err)
		}
		resp, err := p.GenerateData(context.Background(), g, InputOutput{})
		if err != nil {
			t.Fatal(err)
		}

		assertResponse(t, resp, `{"text": "AI reply to JSON"}`)
	})
}

func TestOptionsPatternGenerate(t *testing.T) {
	g, err := genkit.Init(context.Background())
	if err != nil {
		log.Fatal(err)
	}
	testModel := genkit.DefineModel(g, "options", "test", nil, testGenerate)

	t.Run("Streaming", func(t *testing.T) {
		p, err := Define(g, "TestExecute", "TestExecute", WithInputType(InputOutput{}))
		if err != nil {
			t.Fatal(err)
		}

		streamText := ""
		resp, err := p.Generate(
			context.Background(),
			g,
			WithInput(InputOutput{
				Text: "testing",
			}),
			WithStreaming(func(ctx context.Context, grc *ai.ModelResponseChunk) error {
				streamText += grc.Text()
				return nil
			}),
			WithModel(testModel),
			WithContext(&ai.Document{Content: []*ai.Part{ai.NewTextPart("context")}}),
		)
		if err != nil {
			t.Fatal(err)
		}

		assertResponse(t, resp, `AI reply to "TestExecute"`)
		if diff := cmp.Diff(streamText, "stream!"); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
	})

	t.Run("WithModelName", func(t *testing.T) {
		p, err := Define(g, "TestModelname", "TestModelname", WithInputType(InputOutput{}))
		if err != nil {
			t.Fatal(err)
		}

		resp, err := p.Generate(
			context.Background(),
			g,
			WithInput(InputOutput{
				Text: "testing",
			}),
			WithModelName("options/test"),
		)
		if err != nil {
			t.Fatal(err)
		}

		assertResponse(t, resp, `AI reply to "TestModelname"`)
	})
}

func TestGenerateOptions(t *testing.T) {
	g, err := genkit.Init(context.Background())
	if err != nil {
		log.Fatal(err)
	}
	p, err := Define(g, "TestWithGenerate", "TestWithGenerate", WithInputType(InputOutput{}))
	if err != nil {
		t.Fatal(err)
	}

	var tests = []struct {
		name string
		with GenerateOption
	}{
		{
			name: "WithInput",
			with: WithInput(map[string]any{"test": "test"}),
		},
		{
			name: "WithConfig",
			with: WithConfig(&ai.GenerationCommonConfig{}),
		},
		{
			name: "WithContext",
			with: WithContext(&ai.Document{Content: []*ai.Part{ai.NewTextPart("context")}}),
		},
		{
			name: "WithModelName",
			with: WithModelName("defineoptions/test"),
		},
		{
			name: "WithModel",
			with: WithModel(testModel),
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			_, err = p.Generate(
				context.Background(),
				g,
				test.with,
			)

			if err == nil {
				t.Errorf("%s could be set twice", test.name)
			}
		})
	}
}

func assertResponse(t *testing.T, resp *ai.ModelResponse, want string) {
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
	if got != want {
		t.Errorf("fake model replied with %q, want %q", got, want)
	}
}
