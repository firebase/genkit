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

package main

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"google.golang.org/genai"
)

func main() {
	ctx := context.Background()

	// Initialize Genkit with the Google AI plugin. When you pass nil for the
	// Config parameter, the Google AI plugin will get the API key from the
	// GEMINI_API_KEY or GOOGLE_API_KEY environment variable, which is the recommended
	// practice.
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

	// Define a multipart tool.
	// This simulates a tool that "generates" an invitation card
	invitationTool := genkit.DefineMultipartTool(g, "createInvitationCard", "Creates a greeting card",
		func(ctx *ai.ToolContext, input struct {
			Name     string `json:"name"`
			Occasion string `json:"occasion"`
		},
		) (*ai.MultipartToolResponse, error) {
			rectangle := "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHIAAABUAQMAAABk5vEVAAAABlBMVEX///8AAABVwtN+" +
				"AAAAI0lEQVR4nGNgGHaA/z8UHIDwOWASDqP8Uf7w56On/1FAQwAAVM0exw1hqwkAAAAASUVORK5CYII="
			return &ai.MultipartToolResponse{
				Output: map[string]any{"success": true},
				Content: []*ai.Part{
					ai.NewMediaPart("image/png", rectangle),
				},
			}, nil
		},
	)

	type InvitationCard struct {
		Occasion string `json:"occasion"`
	}

	// Define a simple flow that uses the multipart tool
	genkit.DefineStreamingFlow(g, "cardFlow", func(ctx context.Context, input InvitationCard, cb ai.ModelStreamCallback) ([]string, error) {
		resp, err := genkit.Generate(ctx, g,
			ai.WithModelName("googleai/gemini-3-pro-preview"),
			ai.WithConfig(&genai.GenerateContentConfig{
				Temperature: genai.Ptr[float32](1.0),
				ThinkingConfig: &genai.ThinkingConfig{
					ThinkingLevel: genai.ThinkingLevelHigh,
				},
			}),
			ai.WithTools(invitationTool),
			ai.WithStreaming(cb),
			ai.WithPrompt(fmt.Sprintf("Create an invitation card for the following ocassion: %s. Create one for Alex and another one for Pavel", input.Occasion)),
		)
		if err != nil {
			return nil, err
		}

		invitations := []string{}
		for _, m := range resp.History() {
			if m.Role == ai.RoleTool {
				for _, p := range m.Content {
					if p.IsToolResponse() {
						for _, contentPart := range p.ToolResponse.Content {
							if contentPart.IsMedia() {
								invitations = append(invitations, contentPart.Text)
							}
						}
					}
				}
			}
		}
		return invitations, nil
	})

	<-ctx.Done()
}
