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

package prompt

import (
	"context"

	"github.com/firebase/genkit/go/ai"
)

// RenderSystemPrompt renders the system prompt.
func RenderSystemPrompt(ctx context.Context, config *Config, messages []*ai.Message, input map[string]any, raw any) ([]*ai.Message, error) {
	var templateText string
	var err error

	if config.SystemFn != nil {
		templateText, err = config.SystemFn(ctx, raw)
		if err != nil {
			return nil, err
		}
	} else if config.System != "" {
		templateText = config.System
	}

	rendered, err := renderDotprompt(templateText, input, config.DefaultInput)
	if err != nil {
		return nil, err
	}

	if rendered != "" {
		messages = append(messages, &ai.Message{
			Role:    ai.RoleSystem,
			Content: []*ai.Part{ai.NewTextPart(rendered)},
		})
	}

	return messages, nil
}

// RenderUserPrompt renders the user prompt.
func RenderUserPrompt(ctx context.Context, config *Config, messages []*ai.Message, input map[string]any, raw any) ([]*ai.Message, error) {
	var templateText string
	var err error

	if config.PromptFn != nil {
		templateText, err = config.PromptFn(ctx, raw)
		if err != nil {
			return nil, err
		}
	} else if config.Prompt != "" {
		templateText = config.Prompt
	}

	rendered, err := renderDotprompt(templateText, input, config.DefaultInput)
	if err != nil {
		return nil, err
	}

	if rendered != "" {
		messages = append(messages, &ai.Message{
			Role:    ai.RoleUser,
			Content: []*ai.Part{ai.NewTextPart(rendered)},
		})
	}

	return messages, nil
}

func RenderMessages(ctx context.Context, config *Config, messages []*ai.Message, input map[string]any, raw any) ([]*ai.Message, error) {
	var msgs []*ai.Message
	var err error

	if config.MessagesFn != nil {
		msgs, err = config.MessagesFn(ctx, raw)
		if err != nil {
			return nil, err
		}
	} else if len(config.Messages) > 0 {
		msgs = config.Messages
	}

	for _, msg := range msgs {
		for _, part := range msg.Content {
			if part.IsText() {
				rendered, err := renderDotprompt(part.Text, input, config.DefaultInput)
				if err != nil {
					return nil, err
				}
				msg.Content[0].Text = rendered
			}
		}
	}

	return append(messages, msgs...), nil
}
