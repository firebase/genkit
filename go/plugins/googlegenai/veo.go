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
//
// SPDX-License-Identifier: Apache-2.0

package googlegenai

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"google.golang.org/genai"
)

// defineVeoModels defines a new Veo background model for video generation.
// using Google's Veo API through the genai client.
func newVeoModel(
	client *genai.Client,
	name string,
	info ai.ModelOptions,
) ai.BackgroundModel {
	startFunc := func(ctx context.Context, req *ai.ModelRequest) (*ai.ModelOperation, error) {
		// Extract text prompt from the request
		prompt := extractTextFromRequest(req)
		if prompt == "" {
			return nil, fmt.Errorf("no text prompt found in request")
		}

		image := extractVeoImageFromRequest(req)

		videoConfig := toVeoParameters(req)

		operation, err := client.Models.GenerateVideos(
			ctx,
			name,
			prompt,
			image,
			videoConfig,
		)
		if err != nil {
			return nil, fmt.Errorf("veo video generation failed: %w", err)
		}

		return fromVeoOperation(operation), nil
	}

	checkFunc := func(ctx context.Context, op *ai.ModelOperation) (*ai.ModelOperation, error) {
		veoOp, err := checkVeoOperation(ctx, client, op)
		if err != nil {
			return nil, fmt.Errorf("veo operation status check failed: %w", err)
		}

		return fromVeoOperation(veoOp), nil
	}

	return ai.NewBackgroundModel(name, &ai.BackgroundModelOptions{ModelOptions: info}, startFunc, checkFunc)
}

// extractTextFromRequest extracts the text prompt from a model request.
func extractTextFromRequest(request *ai.ModelRequest) string {
	if len(request.Messages) == 0 {
		return ""
	}
	for _, message := range request.Messages {
		for _, part := range message.Content {
			if part.Text != "" {
				return part.Text
			}
		}
	}
	return ""
}

// extractVeoImageFromRequest extracts image content from a model request for Veo.
func extractVeoImageFromRequest(request *ai.ModelRequest) *genai.Image {
	if len(request.Messages) == 0 {
		return nil
	}

	for _, message := range request.Messages {
		for _, part := range message.Content {
			if part.IsMedia() {
				_, data, err := uri.Data(part)
				if err != nil {
					return nil
				}
				return &genai.Image{
					ImageBytes: data,
					MIMEType:   part.ContentType,
				}
			}
		}
	}

	return nil
}

// toVeoParameters converts model request configuration to Veo video generation parameters.
func toVeoParameters(request *ai.ModelRequest) *genai.GenerateVideosConfig {
	params := &genai.GenerateVideosConfig{}
	if request.Config != nil {
		if config, ok := request.Config.(*genai.GenerateVideosConfig); ok {
			return config
		}
	}
	return params
}

// fromVeoOperation converts a Veo API operation to a Genkit core operation.
func fromVeoOperation(veoOp *genai.GenerateVideosOperation) *ai.ModelOperation {
	operation := &ai.ModelOperation{
		ID:       veoOp.Name,
		Done:     veoOp.Done,
		Metadata: make(map[string]any),
	}

	// Handle error cases
	if veoOp.Error != nil {
		if errorMsg, ok := veoOp.Error["message"].(string); ok {
			operation.Error = fmt.Errorf("%s", errorMsg)
		} else {
			operation.Error = fmt.Errorf("operation error: %v", veoOp.Error)
		}
		return operation
	}

	// Handle in-progress operations
	if !veoOp.Done {
		operation.Output = &ai.ModelResponse{
			Message: &ai.Message{
				Role:    ai.RoleModel,
				Content: []*ai.Part{ai.NewTextPart("Video generation in progress...")},
			},
		}
		return operation
	}

	// Handle completed operations with response
	if veoOp.Done && veoOp.Response != nil && veoOp.Response.GeneratedVideos != nil && len(veoOp.Response.GeneratedVideos) > 0 {
		content := make([]*ai.Part, 0, len(veoOp.Response.GeneratedVideos))
		for _, sample := range veoOp.Response.GeneratedVideos {
			if sample.Video != nil && sample.Video.URI != "" {
				content = append(content, ai.NewMediaPart("video/mp4", sample.Video.URI))
			}
		}

		if len(content) > 0 {
			operation.Output = &ai.ModelResponse{
				Message: &ai.Message{
					Role:    ai.RoleModel,
					Content: content,
				},
				FinishReason: ai.FinishReasonStop,
			}
			return operation
		}
	}

	// Handle completed operations without valid response
	operation.Output = &ai.ModelResponse{
		Message: &ai.Message{
			Role:    ai.RoleModel,
			Content: []*ai.Part{ai.NewTextPart("Video generation completed but no videos were generated")},
		},
		FinishReason: ai.FinishReasonStop,
	}

	return operation
}

// checkVeoOperation checks the status of a long-running Veo video generation operation.
func checkVeoOperation(ctx context.Context, client *genai.Client, ops *core.Operation[*ai.ModelResponse]) (*genai.GenerateVideosOperation, error) {
	genaiOps := &genai.GenerateVideosOperation{
		Name: ops.ID,
	}
	return client.Operations.GetVideosOperation(ctx, genaiOps, nil)
}
