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
	"strconv"
	"strings"

	"github.com/firebase/genkit/go/internal/base"
)

type JSONLFormatter struct {
	FormatName string
}

type jsonlHandler struct {
	instructions string
	output       *OutputConfig
}

func (j JSONLFormatter) Name() string {
	return j.FormatName
}

func (j jsonlHandler) Instructions() string {
	return j.instructions
}

func (j jsonlHandler) Config() *OutputConfig {
	return j.output
}

func (j JSONLFormatter) Handler(schema map[string]any) FormatterHandler {
	var instructions string
	if schema != nil && isJSONL(schema) {
		jsonBytes, err := json.Marshal(schema["items"])
		if err != nil {
			instructions = fmt.Sprintf("Error marshalling schema to JSONL: %v", err)
		} else {
			escapedJSON := strconv.Quote(string(jsonBytes))
			instructions = fmt.Sprintf("Output should be JSONL format, a sequence of JSON objects (one per line) separated by a newline '\\n' character. Each line should be a JSON object conforming to the following schema:\n\n```%s```", escapedJSON)
		}
	} else {
		instructions = "Error, schema not valid JSONL"
	}
	constrained := true
	handler := &jsonlHandler{
		instructions: instructions,
		output: &OutputConfig{
			Format:      string(OutputFormatJSONL),
			Schema:      schema,
			Constrained: constrained,
			ContentType: "application/jsonl",
		},
	}

	return handler
}

func (j jsonlHandler) ParseMessage(m *Message) (*Message, error) {
	if j.output != nil && j.output.Format == string(OutputFormatJSONL) {
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
					var schemaBytes []byte
					schemaBytes, err := json.Marshal(j.output.Schema)
					if err != nil {
						return nil, fmt.Errorf("expected schema is not valid: %w", err)
					}
					if err = base.ValidateRaw([]byte(line), schemaBytes); err != nil {
						return nil, err
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

func isJSONL(schema map[string]any) bool {
	sType, ok := schema["type"]

	// If the key doesn't exist or is not an array
	if !ok || sType != "array" {
		return false
	}

	_, ok = schema["items"]
	// If items don't exist
	if !ok {
		return false
	}

	return true
}
