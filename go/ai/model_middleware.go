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

package ai

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"slices"
	"strings"
)

// Provide a simulated system prompt for models that don't support it natively.
func simulateSystemPrompt(info *ModelInfo, options map[string]string) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, input *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
			// Short-circuiting middleware if system role is supported in model.
			if info.Supports.SystemRole {
				return next(ctx, input, cb)
			}
			preface := "SYSTEM INSTRUCTIONS:\n"
			acknowledgement := "Understood."

			if options != nil {
				if p, ok := options["preface"]; ok {
					preface = p
				}
				if a, ok := options["acknowledgement"]; ok {
					acknowledgement = a
				}
			}
			modifiedMessages := make([]*Message, len(input.Messages))
			copy(modifiedMessages, input.Messages)
			for i, message := range input.Messages {
				if message.Role == "system" {
					systemPrompt := message.Content
					userMessage := &Message{
						Role:    "user",
						Content: append([]*Part{NewTextPart(preface)}, systemPrompt...),
					}
					modelMessage := NewModelTextMessage(acknowledgement)

					modifiedMessages = append(modifiedMessages[:i], append([]*Message{userMessage, modelMessage}, modifiedMessages[i+1:]...)...)
					break
				}
			}
			input.Messages = modifiedMessages
			return next(ctx, input, cb)
		}
	}
}

// validateSupport creates middleware that validates whether a model supports the requested features.
func validateSupport(model string, info *ModelInfo) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, input *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
			if info == nil {
				info = &ModelInfo{
					Supports: &ModelSupports{},
					Versions: []string{},
				}
			}

			if !info.Supports.Media {
				for _, msg := range input.Messages {
					for _, part := range msg.Content {
						if part.IsMedia() {
							return nil, fmt.Errorf("model %q does not support media, but media was provided. Request: %+v", model, input)
						}
					}
				}
			}

			if !info.Supports.Tools && len(input.Tools) > 0 {
				return nil, fmt.Errorf("model %q does not support tool use, but tools were provided. Request: %+v", model, input)
			}

			if !info.Supports.Multiturn && len(input.Messages) > 1 {
				return nil, fmt.Errorf("model %q does not support multiple messages, but %d were provided. Request: %+v", model, len(input.Messages), input)
			}

			if !info.Supports.ToolChoice && input.ToolChoice != "" && input.ToolChoice != ToolChoiceAuto {
				return nil, fmt.Errorf("model %q does not support tool choice, but tool choice was provided. Request: %+v", model, input)
			}

			if !info.Supports.SystemRole {
				for _, msg := range input.Messages {
					if msg.Role == RoleSystem {
						return nil, fmt.Errorf("model %q does not support system role, but system role was provided. Request: %+v", model, input)
					}
				}
			}

			if err := validateVersion(model, info.Versions, input.Config); err != nil {
				return nil, err
			}

			// TODO: Add validation for features that won't have simulated support via middleware.

			return next(ctx, input, cb)
		}
	}
}

// validateVersion validates that the requested model version is supported.
func validateVersion(model string, versions []string, config any) error {
	var configMap map[string]any

	switch c := config.(type) {
	case map[string]any:
		configMap = c
	default:
		data, err := json.Marshal(config)
		if err != nil {
			return nil
		}
		if err := json.Unmarshal(data, &configMap); err != nil {
			return nil
		}
	}

	versionVal, exists := configMap["version"]
	if !exists {
		return nil
	}

	version, ok := versionVal.(string)
	if !ok {
		return fmt.Errorf("version must be a string, got %T", versionVal)
	}

	if slices.Contains(versions, version) {
		return nil
	}

	return fmt.Errorf("model %q does not support version %q, supported versions: %v", model, version, versions)
}

func DownloadRequestMedia(options *struct {
	MaxBytes int
	Filter   func(part *Part) bool
}) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, input *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
			client := &http.Client{}
			for _, message := range input.Messages {
				for j, part := range message.Content {
					if !part.IsMedia() || !strings.HasPrefix(part.Text, "http") || (options != nil && options.Filter != nil && !options.Filter(part)) {
						continue
					}

					mediaUrl := part.Text

					resp, err := client.Get(mediaUrl)
					if err != nil {
						return nil, fmt.Errorf("HTTP error downloading media '%s': %v", mediaUrl, err)
					}
					defer resp.Body.Close()

					if resp.StatusCode != http.StatusOK {
						body, _ := io.ReadAll(resp.Body)
						return nil, fmt.Errorf("HTTP error downloading media '%s': %s", mediaUrl, string(body))
					}

					contentType := part.ContentType
					if contentType == "" {
						contentType = resp.Header.Get("Content-Type")
					}

					var data []byte
					if options != nil && options.MaxBytes > 0 {
						limitedReader := io.LimitReader(resp.Body, int64(options.MaxBytes))
						data, err = io.ReadAll(limitedReader)
					} else {
						data, err = io.ReadAll(resp.Body)
					}
					if err != nil {
						return nil, fmt.Errorf("error reading media '%s': %v", mediaUrl, err)
					}

					message.Content[j] = &Part{
						ContentType: contentType,
						Text:        fmt.Sprintf("data:%s;base64,%s", contentType, base64.StdEncoding.EncodeToString(data)),
					}
				}
			}
			return next(ctx, input, cb)
		}
	}
}
