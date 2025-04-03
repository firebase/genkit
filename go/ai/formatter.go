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
)

const (
	regFormatText  = "/format/text"
	regFormatJSON  = "/format/json"
	regFormatJSONL = "/format/jsonl"
)

// Default formats get automatically registered on registry init
var DEFAULT_FORMATS = []Formatter{
	JSONFormatter{FormatName: "json"},
	JSONLFormatter{FormatName: "jsonl"},
	TextFormatter{FormatName: "text"},
}

// Formatter represents the Formatter interface.
type Formatter interface {
	name() string
	handler(schema map[string]any) FormatterHandler
}

// FormatterHandler represents the handler part of the Formatter interface.
type FormatterHandler interface {
	parseMessage(message *Message) (*Message, error)
	instructions() string
	config() *ModelOutputConfig
}

// ConfigureFormats registers default formats in the registry
func ConfigureFormats(reg *registry.Registry) {
	for _, format := range DEFAULT_FORMATS {
		defineFormatter(reg, fmt.Sprintf("/format/%s", format.name()), format)
	}
}

// defineFormatter creates a new Formatter and registers it.
func defineFormatter(
	r *registry.Registry,
	name string,
	formatter Formatter) {
	r.RegisterValue(name, formatter)
}

// resolveFormat returns a Formatter, either a default one or one from the registry
func resolveFormat(reg *registry.Registry, schema map[string]any, format string) (Formatter, error) {
	var formatter any

	// If schema is set but no explicit format is set we default to json.
	if schema != nil && format == "" {
		formatter = reg.LookupValue(regFormatJSON)
	}

	// If format is not set we default to text
	if format == "" {
		formatter = reg.LookupValue(regFormatText)
	}

	// Lookup format in registry
	if format != "" {
		formatter = reg.LookupValue(fmt.Sprintf("/format/%s", format))
	}

	f, ok := formatter.(Formatter)
	if ok {
		return f, nil
	} else {
		return nil, fmt.Errorf("output format %q is invalid", format)
	}
}

// Resolve instructions based on format.
func resolveInstructions(format Formatter, schema map[string]any, instructions *string) string {
	if instructions != nil {
		return *instructions // User provided instructions
	}

	result := format.handler(schema)
	return result.instructions()
}

// shouldInjectFormatInstructions checks GenerateActionOutputConfig and override instruction to determine whether to inject format instructions.
func shouldInjectFormatInstructions(formatConfig *ModelOutputConfig, rawRequestInstructions *string) bool {
	return rawRequestInstructions != nil || !formatConfig.Constrained
}

// simulateConstrainedGeneration simulates constrained generation by injecting generation instructions into the user message.
func simulateConstrainedGeneration(model string, info *ModelInfo) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
			if info == nil {
				info = &ModelInfo{
					Supports: &ModelSupports{},
					Versions: []string{},
				}
			}

			if info.Supports.Constrained == ConstrainedSupportNone || (info.Supports.Constrained == ConstrainedSupportNoTools && len(req.Tools) > 0) {
				// If constrained in model request is set to true and schema is set
				if req.Output.Constrained && req.Output.Schema != nil && len(req.Messages) > 0 {
					instructions, err := defaultInstructions(req.Output.Schema)
					if err != nil {
						return nil, fmt.Errorf("error marshalling schema to JSON for default instructions: %v", err)
					}

					req.Messages = injectInstructions(req.Messages, instructions)
					// we're simulating it, so to the underlying model it's unconstrained.
					req.Output.Constrained = false
				}
			}

			return next(ctx, req, cb)
		}
	}
}

// defaultInstructions returns default instructions to constrain output.
func defaultInstructions(schema map[string]any) (string, error) {
	jsonBytes, err := json.Marshal(schema)
	if err != nil {
		return "", err
	}

	escapedJSON := strconv.Quote(string(jsonBytes))
	instructions := fmt.Sprintf("Output should be in JSON format and conform to the following schema:\n\n```%s```", escapedJSON)
	return instructions, nil
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
