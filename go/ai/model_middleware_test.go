// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"
)

func TestValidateSupport(t *testing.T) {
	tests := []struct {
		name    string
		info    *ModelInfo
		input   *ModelRequest
		wantErr bool
	}{
		{
			name: "valid request with no special features",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{
					Media:      false,
					Tools:      false,
					Multiturn:  false,
					ToolChoice: false,
					SystemRole: false,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
			},
			wantErr: false,
		},
		{
			name: "media not supported but requested",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{
					Media: false,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					{Content: []*Part{NewMediaPart("image/png", "data:image/png;base64,...")}},
				},
			},
			wantErr: true,
		},
		{
			name: "tools not supported but requested",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{
					Tools: false,
				},
			},
			input: &ModelRequest{
				Tools: []*ToolDefinition{
					{
						Name:        "test-tool",
						Description: "A test tool",
					},
				},
			},
			wantErr: true,
		},
		{
			name: "multiturn not supported but requested",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{
					Multiturn: false,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("message 1"),
					NewUserTextMessage("message 2"),
				},
			},
			wantErr: true,
		},
		{
			name: "tool choice not supported but requested",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{
					ToolChoice: false,
				},
			},
			input: &ModelRequest{
				ToolChoice: ToolChoiceRequired,
			},
			wantErr: true,
		},
		{
			name: "system role not supported but requested",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{
					SystemRole: false,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					{Role: RoleSystem, Content: []*Part{NewTextPart("system instruction")}},
				},
			},
			wantErr: true,
		},
		{
			name: "all features supported and used",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{
					Media:      true,
					Tools:      true,
					Multiturn:  true,
					ToolChoice: true,
					SystemRole: true,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewSystemTextMessage("be helpful"),
					NewUserTextMessage("hello! look at this image"),
					{Content: []*Part{NewMediaPart("image/png", "data:image/png;base64,...")}},
				},
				Tools: []*ToolDefinition{
					{
						Name:        "test-tool",
						Description: "A test tool",
					},
				},
				ToolChoice: ToolChoiceNone,
			},
			wantErr: false,
		},
		{
			name: "nil supports defaults to no features",
			info: nil,
			input: &ModelRequest{
				Messages: []*Message{
					{Content: []*Part{NewMediaPart("image/png", "data:image/png;base64,...")}},
				},
			},
			wantErr: true,
		},
		{
			name: "mixed content types in message",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{
					Media: false,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					{Content: []*Part{
						NewTextPart("text content"),
						NewMediaPart("image/png", "data:image/png;base64,..."),
					}},
				},
			},
			wantErr: true,
		},
		{
			name: "supported version",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{},
				Versions: []string{"v1", "v2"},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
				Config: map[string]any{"version": "v1"},
			},
			wantErr: false,
		},
		{
			name: "unsupported version",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{},
				Versions: []string{"v1", "v2"},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
				Config: map[string]any{"version": "v3"},
			},
			wantErr: true,
		},
		{
			name: "non-string version",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{},
				Versions: []string{"v1", "v2"},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
				Config: map[string]any{"version": 1},
			},
			wantErr: true,
		},
		{
			name: "struct with supported version",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{},
				Versions: []string{"v1", "v2"},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
				Config: &GenerationCommonConfig{Version: "v1"},
			},
			wantErr: false,
		},
		{
			name: "struct with unsupported version",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{},
				Versions: []string{"v1", "v2"},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
				Config: &GenerationCommonConfig{Version: "v3"},
			},
			wantErr: true,
		},
	}

	mockModelFunc := func(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
		return &ModelResponse{}, nil
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			handler := ValidateSupport("test-model", tt.info)(mockModelFunc)
			_, err := handler(context.Background(), tt.input, nil)

			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateSupport() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}
		})
	}
}

func TestDownloadRequestMedia(t *testing.T) {
	testCases := []struct {
		name    string
		input   *ModelRequest
		options *struct {
			MaxBytes int
			Filter   func(part *Part) bool
		}
		setupServer    func() *httptest.Server
		expectedResult *ModelRequest
	}{
		{
			name: "successful download",
			input: &ModelRequest{
				Messages: []*Message{
					{
						Content: []*Part{
							{
								ContentType: "image/png",
								Text:        "http://127.0.0.1:60289",
							},
						},
					},
				},
			},
			setupServer: func() *httptest.Server {
				testData := []byte("data:image/png;base64,dGVzdCBpbWFnZSBkYXRh")
				contentType := "image/png"
				ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
					w.Header().Set("Content-Type", contentType)
					w.Write(testData)
				}))
				return ts
			},
			expectedResult: &ModelRequest{
				Messages: []*Message{
					{
						Content: []*Part{
							{
								ContentType: "image/png",
								Text:        "data:image/png;base64,dGVzdCBpbWFnZSBkYXRh",
							},
						},
					},
				},
			},
		},
		{
			name: "base64 media not to download",
			input: &ModelRequest{
				Messages: []*Message{
					{
						Content: []*Part{
							{
								ContentType: "image/png",
								Text:        "data:image/png;base64,dGVzdCBpbWFnZSBkYXRh",
							},
						},
					},
				},
			},
			expectedResult: &ModelRequest{
				Messages: []*Message{
					{
						Content: []*Part{
							{
								ContentType: "image/png",
								Text:        "data:image/png;base64,dGVzdCBpbWFnZSBkYXRh",
							},
						},
					},
				},
			},
		},
		{
			name: "filter applied not satisfied",
			input: &ModelRequest{
				Messages: []*Message{
					{
						Content: []*Part{
							{
								ContentType: "image/png",
								Text:        "http://127.0.0.1:60289",
							},
						},
					},
				},
			},
			options: &struct {
				MaxBytes int
				Filter   func(part *Part) bool
			}{
				Filter: func(part *Part) bool {
					return false
				},
			},
			setupServer: func() *httptest.Server {
				testData := []byte("data:image/png;base64,dGVzdCBpbWFnZSBkYXRh")
				contentType := "image/png"
				ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
					w.Header().Set("Content-Type", contentType)
					w.Write(testData)
				}))
				return ts
			},
			expectedResult: &ModelRequest{
				Messages: []*Message{
					{
						Content: []*Part{
							{
								ContentType: "image/png",
								Text:        "data:image/png;base64,dGVzdCBpbWFnZSBkYXRh",
							},
						},
					},
				},
			},
		},
		{
			name: "filter applied satisfied",
			input: &ModelRequest{
				Messages: []*Message{
					{
						Content: []*Part{
							{
								ContentType: "image/png",
								Text:        "http://127.0.0.1:60289",
							},
						},
					},
				},
			},
			options: &struct {
				MaxBytes int
				Filter   func(part *Part) bool
			}{
				Filter: func(part *Part) bool {
					return true
				},
			},
			expectedResult: &ModelRequest{
				Messages: []*Message{
					{
						Content: []*Part{
							{
								ContentType: "image/png",
								Text:        "http://127.0.0.1:60289",
							},
						},
					},
				},
			},
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			var ts *httptest.Server
			if tc.setupServer != nil {
				ts = tc.setupServer()
				// Get the response body from the test server
				resp, err := http.Get(ts.URL)
				if err != nil {
					t.Fatalf("Error getting test server response: %v", err)
				}
				defer resp.Body.Close()
				body, err := io.ReadAll(resp.Body)
				if err != nil {
					t.Fatalf("Error reading test server response body: %v", err)
				}

				if resp.StatusCode == http.StatusOK {
					// Set the text to the response body
					tc.input.Messages[0].Content[0].Text = string(body)
				}
				defer ts.Close()

			}
			next := func(ctx context.Context, input *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
				return &ModelResponse{}, nil
			}
			middleware := DownloadRequestMedia(tc.options)
			_, err := middleware(next)(context.Background(), tc.input, nil)

			if err != nil {
				t.Errorf("Expected no error, but got: %v", err)
			} else if !reflect.DeepEqual(tc.input, tc.expectedResult) {
				t.Errorf("Expected result: %v, but got: %v", tc.expectedResult, tc.input)
			}

		})
	}
}
