// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"fmt"
)

// ValidateSupport creates middleware that validates whether a model supports the requested features.
func ValidateSupport(model string, supports *ModelInfoSupports) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, input *ModelRequest, cb ModelStreamingCallback) (*ModelResponse, error) {
			if supports == nil {
				supports = &ModelInfoSupports{}
			}

			if !supports.Media {
				for _, msg := range input.Messages {
					for _, part := range msg.Content {
						if part.IsMedia() {
							return nil, fmt.Errorf("model %q does not support media, but media was provided. Request: %+v", model, input)
						}
					}
				}
			}

			if !supports.Tools && len(input.Tools) > 0 {
				return nil, fmt.Errorf("model %q does not support tool use, but tools were provided. Request: %+v", model, input)
			}

			if !supports.Multiturn && len(input.Messages) > 1 {
				return nil, fmt.Errorf("model %q does not support multiple messages, but %d were provided. Request: %+v", model, len(input.Messages), input)
			}

			if !supports.ToolChoice && input.ToolChoice != "" && input.ToolChoice != ToolChoiceAuto {
				return nil, fmt.Errorf("model %q does not support tool choice, but tool choice was provided. Request: %+v", model, input)
			}

			if !supports.SystemRole {
				for _, msg := range input.Messages {
					if msg.Role == RoleSystem {
						return nil, fmt.Errorf("model %q does not support system role, but system role was provided. Request: %+v", model, input)
					}
				}
			}

			// TODO: Add validation for features that won't have simulated support via middleware.

			return next(ctx, input, cb)
		}
	}
}
