// Copyright 2025 Google LLC
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

package compat_oai_test

import (
	"context"
	"os"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/compat_oai"
	"github.com/openai/openai-go"
	openaiClient "github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
	"github.com/stretchr/testify/assert"
)

const defaultModel = "gpt-4o-mini"

func setupTestClient(t *testing.T) *compat_oai.ModelGenerator {
	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		t.Skip("Skipping test: OPENAI_API_KEY environment variable not set")
	}

	client := openaiClient.NewClient(option.WithAPIKey(apiKey))
	return compat_oai.NewModelGenerator(client, defaultModel)
}

func TestGenerator_Complete(t *testing.T) {
	g := setupTestClient(t)

	// define case with user and model messages
	messages := []*ai.Message{
		{
			Role: ai.RoleUser,
			Content: []*ai.Part{
				ai.NewTextPart("Tell me a joke"),
			},
		},
		{
			Role: ai.RoleModel,
			Content: []*ai.Part{
				ai.NewTextPart("Why did the scarecrow win an award?"),
			},
		},
		{
			Role: ai.RoleUser,
			Content: []*ai.Part{
				ai.NewTextPart("Why?"),
			},
		},
	}

	resp, err := g.WithMessages(messages).Generate(context.Background(), nil)
	assert.NoError(t, err)
	assert.NotEmpty(t, resp.Message.Content)
	assert.Equal(t, ai.RoleModel, resp.Message.Role)

	t.Log("\n=== Simple Completion Response ===")
	for _, part := range resp.Message.Content {
		t.Logf("Content: %s", part.Text)
	}
}

func TestGenerator_Stream(t *testing.T) {
	g := setupTestClient(t)

	messages := []*ai.Message{
		{
			Role: ai.RoleUser,
			Content: []*ai.Part{
				ai.NewTextPart("Count from 1 to 3"),
			},
		},
	}

	var chunks []string
	handleChunk := func(ctx context.Context, chunk *ai.ModelResponseChunk) error {
		for _, part := range chunk.Content {
			chunks = append(chunks, part.Text)

			// log each chunk as it arrives
			t.Logf("Chunk: %s", part.Text)
		}
		return nil
	}

	_, err := g.WithMessages(messages).Generate(context.Background(), handleChunk)
	assert.NoError(t, err)
	assert.NotEmpty(t, chunks)

	// Verify we got the full response
	fullText := strings.Join(chunks, "")
	assert.Contains(t, fullText, "1")
	assert.Contains(t, fullText, "2")
	assert.Contains(t, fullText, "3")

	t.Log("\n=== Full Streaming Response ===")
	t.Log(strings.Join(chunks, ""))
}

func TestWithConfig(t *testing.T) {
	tests := []struct {
		name     string
		config   any
		validate func(*testing.T, *openai.ChatCompletionNewParams)
	}{
		{
			name:   "nil config",
			config: nil,
			validate: func(t *testing.T, cfg *openai.ChatCompletionNewParams) {
				// Temperature and MaxTokens should be nil and not present
				assert.False(t, cfg.Temperature.Present)
				assert.False(t, cfg.MaxTokens.Present)
			},
		},
		{
			name: "explicitly set to nil",
			config: &openai.ChatCompletionNewParams{
				Temperature: openai.Null[float64](),
				MaxTokens:   openai.Null[int64](),
			},
			validate: func(t *testing.T, cfg *openai.ChatCompletionNewParams) {
				// Temperature and MaxTokens should be nil and not present
				assert.Equal(t, openai.Null[float64](), cfg.Temperature)
				assert.Equal(t, openai.Null[int64](), cfg.MaxTokens)
			},
		},
		{
			name: "float and int fields",
			config: &openai.ChatCompletionNewParams{
				Temperature: openai.Float(0.5),
				MaxTokens:   openai.Int(100),
			},
			validate: func(t *testing.T, cfg *openai.ChatCompletionNewParams) {
				// Temperature and MaxTokens should be 0.5 and 100 respectively
				assert.Equal(t, openai.Float(0.5), cfg.Temperature)
				assert.Equal(t, openai.Int(100), cfg.MaxTokens)
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			client := &openai.Client{}
			generator := compat_oai.NewModelGenerator(client, "test-model")

			// Apply the config
			generator.WithConfig(tt.config)

			// Get request configuration to validate
			request := generator.GetRequestConfig()

			// Validate the result
			tt.validate(t, request.(*openai.ChatCompletionNewParams))
		})
	}
}
