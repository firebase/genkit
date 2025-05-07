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
	"errors"
	"fmt"
	"regexp"
	"slices"
	"strings"
)

type enumFormatter struct{}

// Name returns the name of the formatter.
func (e enumFormatter) Name() string {
	return OutputFormatEnum
}

// Handler returns a new formatter handler for the given schema.
func (e enumFormatter) Handler(schema map[string]any) (FormatHandler, error) {
	enums := objectEnums(schema)
	if schema == nil || len(enums) == 0 {
		return nil, fmt.Errorf("schema is not valid JSON enum")
	}

	instructions := fmt.Sprintf("Output should be ONLY one of the following enum values. Do not output any additional information or add quotes.\n\n```%s```", strings.Join(enums, "\n"))

	handler := &enumHandler{
		instructions: instructions,
		config: ModelOutputConfig{
			Format:      OutputFormatEnum,
			Schema:      schema,
			ContentType: "text/enum",
		},
		enums: enums,
	}

	return handler, nil
}

type enumHandler struct {
	instructions string
	config       ModelOutputConfig
	enums        []string
}

// Instructions returns the instructions for the formatter.
func (e enumHandler) Instructions() string {
	return e.instructions
}

// Config returns the output config for the formatter.
func (e enumHandler) Config() ModelOutputConfig {
	return e.config
}

// ParseMessage parses the message and returns the formatted message.
func (e enumHandler) ParseMessage(m *Message) (*Message, error) {
	if e.config.Format == OutputFormatEnum {
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

			// replace single and double quotes
			re := regexp.MustCompile(`['"]`)
			clean := re.ReplaceAllString(part.Text, "")

			// trim whitespace
			trimmed := strings.TrimSpace(clean)

			if !slices.Contains(e.enums, trimmed) {
				return nil, fmt.Errorf("message %s not in list of valid enums: %s", trimmed, strings.Join(e.enums, ", "))
			}

			m.Content[i] = NewTextPart(trimmed)
		}
	}

	return m, nil
}

// Get enum strings from json schema
func objectEnums(schema map[string]any) []string {
	var enums []string

	if properties, ok := schema["properties"].(map[string]any); ok {
		for _, propValue := range properties {
			if propMap, ok := propValue.(map[string]any); ok {
				if enumSlice, ok := propMap["enum"].([]any); ok {
					for _, enumVal := range enumSlice {
						if enumStr, ok := enumVal.(string); ok {
							enums = append(enums, enumStr)
						}
					}
				}
			}
		}
	}

	return enums
}
