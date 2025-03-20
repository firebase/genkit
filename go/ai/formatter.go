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

package ai

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/firebase/genkit/go/internal/registry"
	"github.com/invopop/jsonschema"
)

// type Format struct {
// 	Name    string
// 	Config  ModelRequestOutput
// 	Handler func(schema *jsonschema.Schema) FormatterHandler
// }

// Formatter represents the Formatter interface.
type Formatter interface {
	Name() string
	Config() ModelRequestOutput
	Handler(schema *jsonschema.Schema) FormatterHandler
}

// FormatterHandler represents the handler part of the Formatter interface.
type FormatterHandler interface {
	ParseMessage(message *Message) (*Message, error)
	Instructions() string
}

// DefineFormatter creates a new Formatter and registers it.
func DefineFormatter(
	r *registry.Registry,
	name string,
	formatter Formatter) {
	r.RegisterValue("format", name, formatter)
}

//Move validResponse(ctx, resp) to formatter?


// SimulateConstrainedGeneration simulates constrained generation by injecting generation instructions into the user message.
func SimulateConstrainedGeneration(model string, info *ModelInfo) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, input *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
			if info == nil {
				info = &ModelInfo{
					Supports: &ModelInfoSupports{},
					Versions: []string{},
				}
			}

			if info.Supports.Constrained == ConstrainedGenerationNone || (info.Supports.Constrained == ConstrainedGenerationNoTools && len(input.Tools) > 0) {
				// If constrained in model request is set to true and schema is set
				if input.Output != nil && input.Output.Format == OutputFormatJSON && len(input.Messages) > 0 {
					instructions := defaultConstrainedGenerationInstructions(input.Output.Schema)
					input.Messages = injectInstructions(input.Messages, instructions)
					input.Output.Contrained = false
				}
			}

			return next(ctx, input, cb)
		}
	}
}

func defaultConstrainedGenerationInstructions(schema map[string]any) string {
	jsonBytes, err := json.Marshal(schema)
	if err != nil {
		return fmt.Sprintf("Error marshalling schema to JSON: %v", err)
	}

	escapedJSON := strconv.Quote(string(jsonBytes))
	instructions := fmt.Sprintf("Output should be in JSON format and conform to the following schema:\n\n```%s```", escapedJSON)
	return instructions
}

func injectInstructions(messages []*Message, instructions string) []*Message {
	if instructions == "" {
		return messages
	}

	newPart := NewTextPart(instructions)

	// find the system message or the last user message
	targetIndex := -1
	for i, m := range messages {
		if m.Role == "system" {
			targetIndex = i
			break
		}
	}

	if targetIndex == -1 {
		for i := len(messages) - 1; i >= 0; i-- {
			if messages[i].Role == "user" {
				targetIndex = i
				break
			}
		}
	}

	if targetIndex == -1 {
		return messages
	}

	messages[targetIndex].Content = append(messages[targetIndex].Content, newPart)

	return messages
}
