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
	"fmt"
	"os"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/compat_oai"
	openaiClient "github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
	"github.com/stretchr/testify/assert"
)

const defaultModel = "gpt-4o-mini"

func setupTestClient(t *testing.T) *compat_oai.ModelGenerator {
	t.Helper()
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
		err      error
		validate func(*testing.T, *openaiClient.ChatCompletionNewParams)
	}{
		{
			name:   "nil config",
			config: nil,
			validate: func(t *testing.T, request *openaiClient.ChatCompletionNewParams) {
				// For nil config, we expect all fields to be unset (not nil, but with Present=false)
				assert.False(t, request.Temperature.Present)
				assert.False(t, request.MaxCompletionTokens.Present)
				assert.False(t, request.TopP.Present)
				assert.False(t, request.Stop.Present)
			},
		},
		{
			name:   "empty openai config",
			config: compat_oai.OpenAIConfig{},
			validate: func(t *testing.T, request *openaiClient.ChatCompletionNewParams) {
				// For empty config, we expect all fields to be unset
				assert.False(t, request.Temperature.Present)
				assert.False(t, request.MaxCompletionTokens.Present)
				assert.False(t, request.TopP.Present)
				assert.False(t, request.Stop.Present)
			},
		},
		{
			name: "valid config with all supported fields",
			config: compat_oai.OpenAIConfig{
				Temperature:     0.7,
				MaxOutputTokens: 100,
				TopP:            0.9,
				StopSequences:   []string{"stop1", "stop2"},
			},
			validate: func(t *testing.T, request *openaiClient.ChatCompletionNewParams) {
				// Check that fields are present and have correct values
				assert.True(t, request.Temperature.Present)
				assert.Equal(t, float64(0.7), request.Temperature.Value)

				assert.True(t, request.MaxCompletionTokens.Present)
				assert.Equal(t, int64(100), request.MaxCompletionTokens.Value)

				assert.True(t, request.TopP.Present)
				assert.Equal(t, float64(0.9), request.TopP.Value)

				assert.True(t, request.Stop.Present)
				stopArray, ok := request.Stop.Value.(openaiClient.ChatCompletionNewParamsStopArray)
				assert.True(t, ok)
				assert.Equal(t, openaiClient.ChatCompletionNewParamsStopArray{"stop1", "stop2"}, stopArray)
			},
		},
		{
			name: "valid config as map",
			config: map[string]any{
				"temperature":       0.7,
				"max_output_tokens": 100,
				"top_p":             0.9,
				"stop_sequences":    []string{"stop1", "stop2"},
			},
			validate: func(t *testing.T, request *openaiClient.ChatCompletionNewParams) {
				assert.True(t, request.Temperature.Present)
				assert.Equal(t, float64(0.7), request.Temperature.Value)

				assert.True(t, request.MaxCompletionTokens.Present)
				assert.Equal(t, int64(100), request.MaxCompletionTokens.Value)

				assert.True(t, request.TopP.Present)
				assert.Equal(t, float64(0.9), request.TopP.Value)

				assert.True(t, request.Stop.Present)
				stopArray, ok := request.Stop.Value.(openaiClient.ChatCompletionNewParamsStopArray)
				assert.True(t, ok)
				assert.Equal(t, openaiClient.ChatCompletionNewParamsStopArray{"stop1", "stop2"}, stopArray)
			},
		},
		{
			name:   "invalid config type",
			config: "not a config",
			err:    fmt.Errorf("unexpected config type: string"),
		},
	}

	// define simple messages for testing
	messages := []*ai.Message{
		{
			Role: ai.RoleUser,
			Content: []*ai.Part{
				ai.NewTextPart("Tell me a joke"),
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			generator := setupTestClient(t)
			result, err := generator.WithMessages(messages).WithConfig(tt.config).Generate(context.Background(), nil)

			if tt.err != nil {
				assert.Error(t, err)
				assert.Equal(t, tt.err.Error(), err.Error())
				return
			}

			// validate that the response was successful
			assert.NoError(t, err)
			assert.NotNil(t, result)

			// validate the input request was transformed correctly
			if tt.validate != nil {
				tt.validate(t, generator.GetRequest())
			}
		})
	}
}
