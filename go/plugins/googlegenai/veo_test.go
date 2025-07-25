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

package googlegenai

import (
	"context"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"google.golang.org/genai"
)

func TestExtractTextFromRequest(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		request  *ai.ModelRequest
		expected string
	}{
		{
			name: "single text message",
			request: &ai.ModelRequest{
				Messages: []*ai.Message{
					{
						Role: ai.RoleUser,
						Content: []*ai.Part{
							{Text: "Generate a video of a dancing robot"},
						},
					},
				},
			},
			expected: "Generate a video of a dancing robot",
		},
		{
			name: "multiple messages with text",
			request: &ai.ModelRequest{
				Messages: []*ai.Message{
					{
						Role: ai.RoleUser,
						Content: []*ai.Part{
							{Text: "First message"},
						},
					},
					{
						Role: ai.RoleUser,
						Content: []*ai.Part{
							{Text: "Second message"},
						},
					},
				},
			},
			expected: "First message", // Should return the first text found
		},
		{
			name: "empty messages",
			request: &ai.ModelRequest{
				Messages: []*ai.Message{},
			},
			expected: "",
		},
		{
			name: "messages with empty text",
			request: &ai.ModelRequest{
				Messages: []*ai.Message{
					{
						Role: ai.RoleUser,
						Content: []*ai.Part{
							{Text: ""}, // Empty text part
						},
					},
					{
						Role: ai.RoleUser,
						Content: []*ai.Part{
							{Text: "Valid text"},
						},
					},
				},
			},
			expected: "Valid text",
		},
		{
			name:     "nil request",
			request:  &ai.ModelRequest{Messages: nil},
			expected: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := extractTextFromRequest(tt.request)
			if result != tt.expected {
				t.Errorf("extractTextFromRequest() = %q, want %q", result, tt.expected)
			}
		})
	}
}

func TestExtractVeoImageFromRequest(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		request  *ai.ModelRequest
		expected *genai.Image
	}{
		{
			name: "text-only request",
			request: &ai.ModelRequest{
				Messages: []*ai.Message{
					{
						Role: ai.RoleUser,
						Content: []*ai.Part{
							{Text: "Generate a video"},
						},
					},
				},
			},
			expected: nil,
		},
		{
			name: "request with media (not yet implemented)",
			request: &ai.ModelRequest{
				Messages: []*ai.Message{
					{
						Role: ai.RoleUser,
						Content: []*ai.Part{
							ai.NewMediaPart("image/jpeg", "data:image/jpeg;base64,/9j/4AAQ..."),
						},
					},
				},
			},
			expected: nil, // Currently returns nil as implementation is TODO
		},
		{
			name: "empty messages",
			request: &ai.ModelRequest{
				Messages: []*ai.Message{},
			},
			expected: nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := extractVeoImageFromRequest(tt.request)
			if result != tt.expected {
				t.Errorf("extractVeoImageFromRequest() = %v, want %v", result, tt.expected)
			}
		})
	}
}

func TestToVeoParameters(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		request  *ai.ModelRequest
		expected genai.GenerateVideosConfig
	}{
		{
			name: "request with no config",
			request: &ai.ModelRequest{
				Config: nil,
			},
			expected: genai.GenerateVideosConfig{},
		},
		{
			name: "request with valid GenerateVideosConfig",
			request: &ai.ModelRequest{
				Config: &genai.GenerateVideosConfig{
					AspectRatio:      "16:9",
					DurationSeconds:  genai.Ptr(int32(5)),
					PersonGeneration: "allow_adult",
				},
			},
			expected: genai.GenerateVideosConfig{
				AspectRatio:      "16:9",
				DurationSeconds:  genai.Ptr(int32(5)),
				PersonGeneration: "allow_adult",
			},
		},
		{
			name: "request with different config type",
			request: &ai.ModelRequest{
				Config: &genai.GenerateContentConfig{
					MaxOutputTokens: int32(100),
				},
			},
			expected: genai.GenerateVideosConfig{}, // Should return default config
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := toVeoParameters(tt.request)

			// Compare relevant fields since direct comparison might fail due to pointers
			if tt.expected.AspectRatio != "" {
				if result.AspectRatio == "" || result.AspectRatio != tt.expected.AspectRatio {
					t.Errorf("toVeoParameters() AspectRatio = %v, want %v", result.AspectRatio, tt.expected.AspectRatio)
				}
			} else if result.AspectRatio != "" {
				t.Errorf("toVeoParameters() AspectRatio = %v, want nil", result.AspectRatio)
			}

			if tt.expected.DurationSeconds != nil {
				if result.DurationSeconds == nil || *result.DurationSeconds != *tt.expected.DurationSeconds {
					t.Errorf("toVeoParameters() DurationSeconds = %v, want %v", result.DurationSeconds, tt.expected.DurationSeconds)
				}
			} else if result.DurationSeconds != nil {
				t.Errorf("toVeoParameters() DurationSeconds = %v, want nil", result.DurationSeconds)
			}

			if tt.expected.PersonGeneration != "" {
				if result.PersonGeneration == "" || result.PersonGeneration != tt.expected.PersonGeneration {
					t.Errorf("toVeoParameters() PersonGeneration = %v, want %v", result.PersonGeneration, tt.expected.PersonGeneration)
				}
			} else if result.PersonGeneration != "" {
				t.Errorf("toVeoParameters() PersonGeneration = %v, want nil", result.PersonGeneration)
			}
		})
	}
}

func TestFromVeoOperation(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name              string
		veoOp             *genai.GenerateVideosOperation
		expectedID        string
		expectedDone      bool
		expectedError     string
		expectedHasOutput bool
	}{
		{
			name: "pending operation",
			veoOp: &genai.GenerateVideosOperation{
				Name: "operations/test-operation-123",
				Done: false,
			},
			expectedID:        "operations/test-operation-123",
			expectedDone:      false,
			expectedError:     "",
			expectedHasOutput: false,
		},
		{
			name: "completed operation with video",
			veoOp: &genai.GenerateVideosOperation{
				Name: "operations/test-operation-456",
				Done: true,
				Response: &genai.GenerateVideosResponse{
					GeneratedVideos: []*genai.GeneratedVideo{
						{
							Video: &genai.Video{
								URI: "https://storage.googleapis.com/test-bucket/video123.mp4",
							},
						},
					},
				},
			},
			expectedID:        "operations/test-operation-456",
			expectedDone:      true,
			expectedError:     "",
			expectedHasOutput: true,
		},
		{
			name: "operation with error",
			veoOp: &genai.GenerateVideosOperation{
				Name: "operations/test-operation-error",
				Done: true,
				Error: map[string]any{
					"message": "Video generation failed due to content policy",
					"code":    400,
				},
			},
			expectedID:        "operations/test-operation-error",
			expectedDone:      true,
			expectedError:     "Video generation failed due to content policy",
			expectedHasOutput: false,
		},
		{
			name: "operation with malformed error",
			veoOp: &genai.GenerateVideosOperation{
				Name: "operations/test-operation-bad-error",
				Done: true,
				Error: map[string]any{
					"code":    500,
					"details": "Internal error",
					// No "message" field
				},
			},
			expectedID:        "operations/test-operation-bad-error",
			expectedDone:      true,
			expectedError:     "operation error: map[code:500 details:Internal error]",
			expectedHasOutput: false,
		},
		{
			name: "completed operation with multiple videos",
			veoOp: &genai.GenerateVideosOperation{
				Name: "operations/test-operation-multi",
				Done: true,
				Response: &genai.GenerateVideosResponse{
					GeneratedVideos: []*genai.GeneratedVideo{
						{
							Video: &genai.Video{
								URI: "https://storage.googleapis.com/test-bucket/video1.mp4",
							},
						},
						{
							Video: &genai.Video{
								URI: "https://storage.googleapis.com/test-bucket/video2.mp4",
							},
						},
					},
				},
			},
			expectedID:        "operations/test-operation-multi",
			expectedDone:      true,
			expectedError:     "",
			expectedHasOutput: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := fromVeoOperation(tt.veoOp)

			// Check basic operation fields
			if result.ID != tt.expectedID {
				t.Errorf("fromVeoOperation() ID = %q, want %q", result.ID, tt.expectedID)
			}

			if result.Done != tt.expectedDone {
				t.Errorf("fromVeoOperation() Done = %t, want %t", result.Done, tt.expectedDone)
			}

			if result.Error != tt.expectedError {
				t.Errorf("fromVeoOperation() Error = %q, want %q", result.Error, tt.expectedError)
			}

			// Check output presence
			hasOutput := result.Output != nil
			if hasOutput != tt.expectedHasOutput {
				t.Errorf("fromVeoOperation() has output = %t, want %t", hasOutput, tt.expectedHasOutput)
			}

			// If we expect output, validate it's a ModelResponse with correct structure
			if tt.expectedHasOutput && result.Output != nil {
				modelResp, ok := result.Output.(*ai.ModelResponse)
				if !ok {
					t.Errorf("fromVeoOperation() Output is not *ai.ModelResponse, got %T", result.Output)
				} else {
					if modelResp.Message == nil {
						t.Error("fromVeoOperation() ModelResponse.Message is nil")
					} else {
						if modelResp.Message.Role != ai.RoleModel {
							t.Errorf("fromVeoOperation() Message.Role = %v, want %v", modelResp.Message.Role, ai.RoleModel)
						}

						if len(modelResp.Message.Content) == 0 {
							t.Error("fromVeoOperation() Message.Content is empty")
						} else {
							// Verify first content part is a media part
							firstPart := modelResp.Message.Content[0]
							if !firstPart.IsMedia() {
								t.Error("fromVeoOperation() first content part is not media")
							}
						}

						if modelResp.FinishReason != ai.FinishReasonStop {
							t.Errorf("fromVeoOperation() FinishReason = %v, want %v", modelResp.FinishReason, ai.FinishReasonStop)
						}
					}
				}
			}
		})
	}
}

func TestGetVeoConfigSchema(t *testing.T) {
	t.Parallel()

	schema := getVeoConfigSchema()
	if schema == nil {
		t.Error("getVeoConfigSchema() returned nil")
		return
	}

	// Verify that the schema has some expected properties
	// Note: This is a basic validation since the exact schema depends on the genai.GenerateVideosConfig struct
	if schema.Type == "" {
		t.Error("getVeoConfigSchema() schema.Type is nil")
	}
}

// TestCheckVeoOperation tests the checkVeoOperation function with a mock scenario
// Note: This is a basic structure test. In a real scenario, you'd need to mock the genai.Client
func TestCheckVeoOperationStructure(t *testing.T) {
	t.Parallel()

	// Test the function signature and basic structure
	ctx := context.Background()

	// This test verifies the function exists and has the correct signature
	// In a real test environment, you would mock the genai.Client and its methods

	ops := &core.Operation{
		ID:   "operations/test-123",
		Done: false,
	}

	// We can't easily test this without mocking the genai.Client
	// But we can verify the function exists and the parameters are correctly typed
	var client *genai.Client = nil // This would be a mock in real tests

	if client != nil {
		_, err := checkVeoOperation(ctx, client, ops)
		if err != nil {
			t.Logf("checkVeoOperation returned expected error with nil client: %v", err)
		}
	} else {
		t.Log("checkVeoOperation function structure test passed (mock client would be needed for full test)")
	}
}
