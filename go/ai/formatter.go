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
	"fmt"

	"github.com/firebase/genkit/go/core/api"
)

const (
	// OutputFormatText is the default format.
	OutputFormatText string = "text"
	// OutputFormatJSON is the legacy format for JSON content. It modifies the message content in place by stripping out non-JSON content.
	//
	// Deprecated: Use OutputFormatJSONV2 instead.
	OutputFormatJSON string = "json"
	// OutputFormatJSONV2 is the format for JSON content.
	OutputFormatJSONV2 string = "json.v2"
	// OutputFormatJSONL is the legacy format for JSONL content. It modifies the message content in place by splitting out a single text part into multiple JSON parts, one per JSON object line.
	// It does not support [ModelResponse.Output] to an array; each JSON part must be unmarshaled manually.
	//
	// Deprecated: Use OutputFormatJSONLV2 instead.
	OutputFormatJSONL string = "jsonl"
	// OutputFormatJSONLV2 is the format for JSONL content.
	OutputFormatJSONLV2 string = "jsonl.v2"
	// OutputFormatMedia is the format for media content.
	OutputFormatMedia string = "media"
	// OutputFormatArray is the format for array content.
	OutputFormatArray string = "array"
	// OutputFormatEnum is the format for enum content.
	OutputFormatEnum string = "enum"
)

// Default formats get automatically registered on registry init
var DEFAULT_FORMATS = []Formatter{
	textFormatter{},
	jsonFormatter{},
	jsonFormatter{v2: true},
	jsonlFormatter{},
	jsonlFormatter{v2: true},
	arrayFormatter{},
	enumFormatter{},
}

// Formatter represents the Formatter interface.
type Formatter interface {
	// Name returns the name of the formatter.
	Name() string
	// Handler returns the handler for the formatter.
	Handler(schema map[string]any) (FormatHandler, error)
}

// FormatHandler is a handler for formatting messages.
// A new instance is created via [Formatter.Handler] for each request.
type FormatHandler interface {
	// ParseMessage parses the message and returns a new formatted message.
	//
	// Legacy: New format handlers should implement this as a no-op passthrough and implement [StreamingFormatHandler] instead.
	ParseMessage(message *Message) (*Message, error)
	// Instructions returns the formatter instructions to embed in the prompt.
	Instructions() string
	// Config returns the output config for the model request.
	Config() ModelOutputConfig
}

// StreamingFormatHandler is a handler for formatting messages that supports streaming.
// This interface must be implemented to be able to use [ModelResponse.Output] and [ModelResponseChunk.Output].
type StreamingFormatHandler interface {
	// ParseOutput parses the final output and returns parsed output.
	ParseOutput(message *Message) (any, error)
	// ParseChunk processes a streaming chunk and returns parsed output.
	// The handler maintains its own internal state. When the chunk's index changes, the state is reset for the new turn.
	// Returns parsed output, or nil if nothing can be parsed yet.
	ParseChunk(chunk *ModelResponseChunk) (any, error)
}

// ConfigureFormats registers default formats in the registry
func ConfigureFormats(reg api.Registry) {
	for _, format := range DEFAULT_FORMATS {
		DefineFormat(reg, "/format/"+format.Name(), format)
	}
}

// DefineFormat defines and registers a new [Formatter].
func DefineFormat(r api.Registry, name string, formatter Formatter) {
	r.RegisterValue(name, formatter)
}

// resolveFormat returns a [Formatter], either a default one or one from the registry.
func resolveFormat(reg api.Registry, schema map[string]any, format string) (Formatter, error) {
	var formatter any

	// If schema is set but no explicit format is set we default to json.
	if schema != nil && format == "" {
		formatter = reg.LookupValue("/format/" + OutputFormatJSON)
	}

	// If format is not set we default to text
	if format == "" {
		formatter = reg.LookupValue("/format/" + OutputFormatText)
	}

	// Lookup format in registry
	if format != "" {
		formatter = reg.LookupValue("/format/" + format)
	}

	if f, ok := formatter.(Formatter); ok {
		return f, nil
	}

	return nil, fmt.Errorf("output format %q is invalid", format)
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

	part := NewTextPart(instructions)
	part.Metadata = map[string]any{"purpose": "output"}

	targetIndex := -1

	// First try to find a system message
	for i, m := range messages {
		if m.Role == RoleSystem {
			targetIndex = i
			break
		}
	}

	// If no system message, find the last user message
	if targetIndex == -1 {
		for i := len(messages) - 1; i >= 0; i-- {
			if messages[i].Role == RoleUser {
				targetIndex = i
				break
			}
		}
	}

	if targetIndex != -1 {
		messages[targetIndex].Content = append(messages[targetIndex].Content, part)
	}

	return messages
}
