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
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"github.com/firebase/genkit/go/internal/base"
)

type jsonlFormatter struct {
	stateless bool
}

// Name returns the name of the formatter.
func (j jsonlFormatter) Name() string {
	if j.stateless {
		return OutputFormatJSONLV2
	}
	return OutputFormatJSONL
}

// Handler returns a new formatter handler for the given schema.
func (j jsonlFormatter) Handler(schema map[string]any) (FormatHandler, error) {
	if schema == nil || !base.ValidateIsJSONArray(schema) {
		return nil, fmt.Errorf("schema is not valid JSONL")
	}

	jsonBytes, err := json.Marshal(schema["items"])
	if err != nil {
		return nil, fmt.Errorf("error marshalling schema to JSONL: %w", err)
	}

	instructions := fmt.Sprintf("Output should be JSONL format, a sequence of JSON objects (one per line) separated by a newline '\\n' character. Each line should be a JSON object conforming to the following schema:\n\n```%s```", string(jsonBytes))

	format := OutputFormatJSONL
	if j.stateless {
		format = OutputFormatJSONLV2
	}

	handler := &jsonlHandler{
		stateless:    j.stateless,
		instructions: instructions,
		config: ModelOutputConfig{
			Format:      format,
			Schema:      schema,
			ContentType: "application/jsonl",
		},
	}

	return handler, nil
}

type jsonlHandler struct {
	stateless       bool
	instructions    string
	config          ModelOutputConfig
	accumulatedText string
	currentIndex    int
}

// Instructions returns the instructions for the formatter.
func (j *jsonlHandler) Instructions() string {
	return j.instructions
}

// Config returns the output config for the formatter.
func (j *jsonlHandler) Config() ModelOutputConfig {
	return j.config
}

// parseJSONL is the shared parsing logic used by both ParseOutput and ParseChunk.
func (j *jsonlHandler) parseJSONL(text string, allowPartial bool) []any {
	if text == "" {
		return []any{}
	}

	results := []any{}
	lines := strings.Split(text, "\n")

	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		isLastLine := i == len(lines)-1

		if strings.HasPrefix(trimmed, "{") {
			var result any
			err := json.Unmarshal([]byte(trimmed), &result)
			if err != nil {
				if allowPartial && isLastLine {
					partialResult, partialErr := base.ParsePartialJSON(trimmed)
					if partialErr == nil && partialResult != nil {
						results = append(results, partialResult)
					}
				}
				continue
			}
			if result != nil {
				results = append(results, result)
			}
		}
	}

	return results
}

// ParseOutput parses the final message and returns the parsed array of objects.
func (j *jsonlHandler) ParseOutput(m *Message) (any, error) {
	return j.parseJSONL(m.Text(), false), nil
}

// ParseChunk processes a streaming chunk and returns parsed output.
func (j *jsonlHandler) ParseChunk(chunk *ModelResponseChunk) (any, error) {
	if chunk.Index != j.currentIndex {
		j.accumulatedText = ""
		j.currentIndex = chunk.Index
	}

	for _, part := range chunk.Content {
		if part.IsText() {
			j.accumulatedText += part.Text
		}
	}

	return j.parseJSONL(j.accumulatedText, true), nil
}

// ParseMessage parses the message and returns the formatted message.
func (j *jsonlHandler) ParseMessage(m *Message) (*Message, error) {
	if j.stateless {
		return m, nil
	}

	if m == nil {
		return nil, errors.New("message is empty")
	}
	if len(m.Content) == 0 {
		return nil, errors.New("message has no content")
	}

	var nonTextParts []*Part
	accumulatedText := strings.Builder{}

	for _, part := range m.Content {
		if !part.IsText() {
			nonTextParts = append(nonTextParts, part)
		} else {
			accumulatedText.WriteString(part.Text)
		}
	}

	var newParts []*Part
	lines := base.GetJSONObjectLines(accumulatedText.String())
	for _, line := range lines {
		if j.config.Schema != nil {
			var schemaBytes []byte
			schemaBytes, err := json.Marshal(j.config.Schema["items"])
			if err != nil {
				return nil, fmt.Errorf("expected schema is not valid: %w", err)
			}
			if err = base.ValidateRaw([]byte(line), schemaBytes); err != nil {
				return nil, err
			}
		}

		newParts = append(newParts, NewJSONPart(line))
	}

	m.Content = append(newParts, nonTextParts...)

	return m, nil
}
