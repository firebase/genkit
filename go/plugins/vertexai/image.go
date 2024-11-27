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

package vertexai

import (
	"cloud.google.com/go/vertexai/genai"
	"context"
	"fmt"
	"github.com/firebase/genkit/go/ai"
)

func imagenModel(
	ctx context.Context,
	client *genai.Client,
	model string,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	gm := client.GenerativeModel(model)

	var prompt string
	if len(input.Messages) > 0 {
		prompt = input.Messages[len(input.Messages)-1].Text()
	}

	parts := []genai.Part{genai.Text(prompt)}
	if meta, ok := input.Config.(*ImagenParameters); ok {
		if meta.NegativePrompt != "" {
			parts = append(parts, genai.Blob{
				Data:     []byte(meta.NegativePrompt),
				MIMEType: "application/x-negative-prompt",
			})
		}
	}

	resp, err := gm.GenerateContent(ctx, parts...)
	if err != nil {
		return nil, fmt.Errorf("error generating content: %w", err)
	}

	m := &ai.ModelResponse{
		Usage: &ai.GenerationUsage{
			Custom: map[string]float64{
				"promptTokenCount":     float64(resp.UsageMetadata.PromptTokenCount),
				"candidatesTokenCount": float64(resp.UsageMetadata.CandidatesTokenCount),
				"totalTokenCount":      float64(resp.UsageMetadata.TotalTokenCount),
			},
		},
	}
	for _, cand := range resp.Candidates {
		if cb != nil {
			err := cb(ctx, &ai.ModelResponseChunk{
				Content: partsFromContent(cand.Content),
			})
			if err != nil {
				return nil, err
			}
		}
		m.Message = &ai.Message{
			Role:    ai.RoleModel,
			Content: partsFromContent(cand.Content),
		}
	}
	return m, nil
}

func partsFromContent(content *genai.Content) []*ai.Part {
	var parts []*ai.Part
	for _, part := range content.Parts {
		switch p := part.(type) {
		case genai.Text:
			parts = append(parts, ai.NewTextPart(string(p)))
		case genai.FileData:
			parts = append(parts, ai.NewMediaPart(p.MIMEType, p.FileURI))
		}
	}
	return parts
}

func configFromRequest(req *ai.ModelRequest) *genai.GenerationConfig {
	config := &genai.GenerationConfig{}
	if meta, ok := req.Config.(*ImagenParameters); ok {
		config.StopSequences = []string{meta.NegativePrompt}
	}
	return config
}

type ImagenParameters struct {
	MaskImage         string `json:"maskImage,omitempty"`
	AdhereToMaskImage string `json:"adhereToMaskImage,omitempty"`
	NegativePrompt    string `json:"negativePrompt,omitempty"`
}
