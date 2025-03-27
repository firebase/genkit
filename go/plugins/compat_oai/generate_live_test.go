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
