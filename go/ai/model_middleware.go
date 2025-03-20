// Copyright 2024 Google LLC
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

// ValidateSupport creates middleware that validates whether a model supports the requested features.
func ValidateSupport(model string, info *ModelInfo) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, input *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
			if info == nil {
				info = &ModelInfo{
					Supports: &ModelInfoSupports{},
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
