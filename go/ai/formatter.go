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
	"errors"
	"fmt"
	"strconv"

	"github.com/firebase/genkit/go/internal/registry"
)

var DEFAULT_FORMATS = []Formatter{
	JSONFormatter{FormatName: "json"},
	TextFormatter{FormatName: "text"},
}

// Formatter represents the Formatter interface.
type Formatter interface {
	Name() string
	Config() OutputConfig
	Handler(schema map[string]any) FormatterHandler
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

func ConfigureFormats(reg *registry.Registry) {
	for _, format := range DEFAULT_FORMATS {
		DefineFormatter(reg,
			format.Name(),
			format,
		)
	}
}

func ResolveFormat(reg *registry.Registry, config *OutputConfig) (Formatter, error) {
	var formatter any

	if config.Format == "" {
		formatter = reg.LookupValue("/format/text")
	}

	if config.Schema != nil && config.Format == "" {
		formatter = reg.LookupValue("/format/json")
	}

	if config.Format != "" {
		formatter = reg.LookupValue(fmt.Sprintf("/format/%s", config.Format))
	}

	f, ok := formatter.(Formatter)
	if ok {
		return f, nil
	} else {
		return nil, errors.New("invalid output format")
	}
}

// SimulateConstrainedGeneration simulates constrained generation by injecting generation instructions into the user message.
func SimulateConstrainedGeneration(model string, info *ModelInfo) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
			if info == nil {
				info = &ModelInfo{
					Supports: &ModelInfoSupports{},
					Versions: []string{},
				}
			}

			if info.Supports.Constrained == ModelInfoSupportsConstrainedNone || (info.Supports.Constrained == ModelInfoSupportsConstrainedNoTools && len(req.Tools) > 0) {
				// If constrained in model request is set to true and schema is set
				if req.Output.Format == string(OutputFormatJSON) && req.Output.Schema != nil && len(req.Messages) > 0 {
					instructions := defaultConstrainedGenerationInstructions(req.Output.Schema)
					req.Messages = injectInstructions(req.Messages, instructions)
					// we're simulating it, so to the underlying model it's unconstrained.
					req.Output.Constrained = false
				}
			}

			return next(ctx, req, cb)
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
