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

package ai

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/core"
)

// ValidateSupport creates middleware that validates whether a model supports the requested features.
func ValidateSupport(name string, supports *ModelInfoSupports) ModelMiddleware {
	return func(ctx context.Context, input *ModelRequest, cb ModelStreamingCallback, next core.Func[*ModelRequest, *ModelResponse, *ModelResponseChunk]) (*ModelResponse, error) {
		if supports == nil {
			supports = &ModelInfoSupports{}
		}

		if !supports.Media {
			for _, msg := range input.Messages {
				for _, part := range msg.Content {
					if part.IsMedia() {
						return nil, fmt.Errorf("model %q does not support media, but media was provided. Request: %+v", name, input)
					}
				}
			}
		}

		if !supports.Tools && len(input.Tools) > 0 {
			return nil, fmt.Errorf("model %q does not support tool use, but tools were provided. Request: %+v", name, input)
		}

		if !supports.Multiturn && len(input.Messages) > 1 {
			return nil, fmt.Errorf("model %q does not support multiple messages, but %d were provided. Request: %+v", name, len(input.Messages), input)
		}

		// TODO: Add validation for features that won't have simulated support via middleware.

		return next(ctx, input, cb)
	}
}
