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

		return next(ctx, input, cb)
	}
}
