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

	"github.com/firebase/genkit/go/internal/base"
)

type JSONFormatter struct {
	FormatName string
	output     OutputConfig
}

type jsonHandler struct {
	instructions string
	output       *OutputConfig
}

func (j JSONFormatter) Name() string {
	return j.FormatName
}

func (j jsonHandler) Instructions() string {
	return j.instructions
}

func (j jsonHandler) Config() *OutputConfig {
	return j.output
}

func (j JSONFormatter) Handler(schema map[string]any) FormatterHandler {
	var instructions string
	if schema != nil {
		jsonBytes, err := json.Marshal(schema)
		if err != nil {
			instructions = fmt.Sprintf("Error marshalling schema to JSON: %v", err)
		} else {
			escapedJSON := strconv.Quote(string(jsonBytes))
			instructions = fmt.Sprintf("Output should be in JSON format and conform to the following schema:\n\n```%s```", escapedJSON)
		}
	}
	constrained := true
	handler := &jsonHandler{
		instructions: instructions,
		output: &OutputConfig{
			Format:      string(OutputFormatJSON),
			Schema:      schema,
			Constrained: constrained,
			ContentType: "application/json",
		},
	}

	return handler
}

func (j jsonHandler) ParseMessage(m *Message) (*Message, error) {
	if j.output != nil && j.output.Format == string(OutputFormatJSON) {
		if m == nil {
			return nil, errors.New("message is empty")
		}
		if len(m.Content) == 0 {
			return nil, errors.New("message has no content")
		}

		for i, part := range m.Content {
			if !part.IsText() {
				continue
			}

			text := base.ExtractJSONFromMarkdown(part.Text)

			var schemaBytes []byte
			schemaBytes, err := json.Marshal(j.output.Schema)
			if err != nil {
				return nil, fmt.Errorf("expected schema is not valid: %w", err)
			}
			if err = base.ValidateRaw([]byte(text), schemaBytes); err != nil {
				return nil, err
			}

			m.Content[i] = NewJSONPart(text)
		}
	}
	return m, nil
}
