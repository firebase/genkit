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

// Default formats get automatically registered on registry init
var DEFAULT_FORMATS = []Formatter{
	JSONFormatter{FormatName: "json"},
	TextFormatter{FormatName: "text"},
}

// Formatter represents the Formatter interface.
type Formatter interface {
	Name() string
	Handler(schema map[string]any) FormatterHandler
}

// FormatterHandler represents the handler part of the Formatter interface.
type FormatterHandler interface {
	ParseMessage(message *Message) (*Message, error)
	Instructions() string
	Config() *GenerateActionOutputConfig
}

// DefineFormatter creates a new Formatter and registers it.
func DefineFormatter(
	r *registry.Registry,
	name string,
	formatter Formatter) {
	r.RegisterValue("format", name, formatter)
}

// ConfigureFormats registers default formats in the registry
func ConfigureFormats(reg *registry.Registry) {
	for _, format := range DEFAULT_FORMATS {
		DefineFormatter(reg,
			format.Name(),
			format,
		)
	}
}

// ResolveFormat returns a Formatter, either a default one or one from the registry
func ResolveFormat(reg *registry.Registry, schema map[string]any, format string) (Formatter, error) {
	var formatter any

	// If schema is set but no explicit format is set we default to json.
	if schema != nil && format == "" {
		formatter = reg.LookupValue("/format/json")
	}

	// If format is not set we default to text
	if format == "" {
		formatter = reg.LookupValue("/format/text")
	}

	// Lookup format in registry
	if format != "" {
		formatter = reg.LookupValue(fmt.Sprintf("/format/%s", format))
	}

	f, ok := formatter.(Formatter)
	if ok {
		return f, nil
	} else {
		return nil, errors.New("invalid output format")
	}
}

// Resolve instructions based on format.
func ResolveInstructions(format Formatter, schema map[string]any, instructions string) string {
	if instructions != "" {
		return instructions // User provided instructions
	}

	result := format.Handler(schema)
	return result.Instructions()
}

// ShouldInjectFormatInstructions checks GenerateActionOutputConfig and override instruction to determine whether to inject format instructions.
func ShouldInjectFormatInstructions(formatConfig *GenerateActionOutputConfig, rawRequestInstructions *bool) bool {
	return formatConfig.Instructions != "" || !formatConfig.Constrained || (rawRequestInstructions != nil && *rawRequestInstructions)
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
				if req.Output.Constrained && req.Output.Schema != nil && len(req.Messages) > 0 {
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

// Default constrained generation instructions.
func defaultConstrainedGenerationInstructions(schema map[string]any) string {
	jsonBytes, err := json.Marshal(schema)
	if err != nil {
		return fmt.Sprintf("Error marshalling schema to JSON: %v", err)
	}

	escapedJSON := strconv.Quote(string(jsonBytes))
	instructions := fmt.Sprintf("Output should be in JSON format and conform to the following schema:\n\n```%s```", escapedJSON)
	return instructions
}

// injectInstructions looks through the messages and injects formatting directives
func injectInstructions(messages []*Message, instructions string) []*Message {
	if instructions == "" {
		return messages
	}

	// bail out if an output part is already present
	for _, m := range messages {
		for _, p := range m.Content {
			if p.Metadata != nil && p.Metadata["purpose"] == "output" {
				return messages
			}
		}
	}

	newPart := &Part{
		Kind:        PartText,
		ContentType: "plain/text",
		Text:        instructions,
		Metadata:    map[string]any{"purpose": "output"},
	}

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
