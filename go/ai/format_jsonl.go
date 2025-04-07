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

type jsonlFormatter struct{}

// Name returns the name of the formatter.
func (j jsonlFormatter) Name() string {
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

	handler := &jsonlHandler{
		instructions: instructions,
		config: ModelOutputConfig{
			Format:      OutputFormatJSONL,
			Schema:      schema,
			ContentType: "application/jsonl",
		},
	}

	return handler, nil
}

type jsonlHandler struct {
	instructions string
	config       ModelOutputConfig
}

// Instructions returns the instructions for the formatter.
func (j jsonlHandler) Instructions() string {
	return j.instructions
}

// Config returns the output config for the formatter.
func (j jsonlHandler) Config() ModelOutputConfig {
	return j.config
}

// ParseMessage parses the message and returns the formatted message.
func (j jsonlHandler) ParseMessage(m *Message) (*Message, error) {
	if j.config.Format == OutputFormatJSONL {
		if m == nil {
			return nil, errors.New("message is empty")
		}
		if len(m.Content) == 0 {
			return nil, errors.New("message has no content")
		}

		var newParts []*Part
		for _, part := range m.Content {
			if !part.IsText() {
				newParts = append(newParts, part)
			} else {
				lines := objectLines(part.Text)
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
			}
		}
		m.Content = newParts
	}

	return m, nil
}

// objectLines splits a string by newlines, trims whitespace from each line,
// and returns a slice containing only the lines that start with '{'.
func objectLines(text string) []string {
	jsonText := base.ExtractJSONFromMarkdown(text)

	// Handle both actual "\n" newline strings, as well as newline bytes
	jsonText = strings.ReplaceAll(jsonText, "\n", `\n`)

	// Split the input string into lines based on the newline character.
	lines := strings.Split(jsonText, `\n`)

	var result []string
	for _, line := range lines {
		if line == "" {
			continue
		}

		// Trim leading and trailing whitespace from the current line.
		trimmedLine := strings.TrimSpace(line)
		// Check if the trimmed line starts with the character '{'.
		if strings.HasPrefix(trimmedLine, "{") {
			// If it does, append the trimmed line to our result slice.
			result = append(result, trimmedLine)
		}
	}

	// Return the slice containing the filtered and trimmed lines.
	return result
}
