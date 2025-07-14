// Copyright 2025 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package base

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"os"
	"reflect"
	"regexp"
	"strings"

	"github.com/invopop/jsonschema"
)

// JSONString returns json.Marshal(x) as a string. If json.Marshal returns
// an error, jsonString returns the error text as a JSON string beginning "ERROR:".
func JSONString(x any) string {
	bytes, err := json.Marshal(x)
	if err != nil {
		bytes, _ = json.Marshal(fmt.Sprintf("ERROR: %v", err))
	}
	return string(bytes)
}

// PrettyJSONString returns json.MarshalIndent(x, "", "  ") as a string.
// If json.MarshalIndent returns an error, jsonString returns the error text as
// a JSON string beginning "ERROR:".
func PrettyJSONString(x any) string {
	bytes, err := json.MarshalIndent(x, "", "  ")
	if err != nil {
		bytes, _ = json.MarshalIndent(fmt.Sprintf("ERROR: %v", err), "", "  ")
	}
	return string(bytes)
}

// WriteJSONFile writes value to filename as JSON.
func WriteJSONFile(filename string, value any) error {
	f, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer func() {
		err = errors.Join(err, f.Close())
	}()
	enc := json.NewEncoder(f)
	enc.SetIndent("", "    ") // make the value easy to read for debugging
	return enc.Encode(value)
}

// ReadJSONFile JSON-decodes the contents of filename into pvalue,
// which must be a pointer.
func ReadJSONFile(filename string, pvalue any) error {
	f, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer f.Close()
	return json.NewDecoder(f).Decode(pvalue)
}

func InferJSONSchema(x any) (s *jsonschema.Schema) {
	r := jsonschema.Reflector{
		DoNotReference: true,
		Mapper: func(t reflect.Type) *jsonschema.Schema {
			// []any generates `{ type: "array", items: true }` which is not valid JSON schema.
			if t.Kind() == reflect.Slice && t.Elem().Kind() == reflect.Interface {
				return &jsonschema.Schema{
					Type: "array",
					Items: &jsonschema.Schema{
						// This field is not necessary but it's the most benign way for the object to not be empty.
						AdditionalProperties: jsonschema.TrueSchema,
					},
				}
			}
			return nil // Return nil to use default schema generation for other types
		},
	}
	s = r.Reflect(x)
	// TODO: Unwind this change once Monaco Editor supports newer than JSON schema draft-07.
	s.Version = ""
	return s
}

// SchemaAsMap converts json schema struct to a map (JSON representation).
func SchemaAsMap(s *jsonschema.Schema) map[string]any {
	jsb, err := s.MarshalJSON()
	if err != nil {
		log.Panicf("failed to marshal schema: %v", err)
	}

	// Check if the marshaled JSON is "true" (indicates an empty schema)
	if string(jsb) == "true" {
		return make(map[string]any)
	}

	var m map[string]any
	err = json.Unmarshal(jsb, &m)
	if err != nil {
		log.Panicf("failed to unmarshal schema: %v", err)
	}
	return m
}

var jsonMarkdownRegex = regexp.MustCompile("```(json)?((\n|.)*?)```")

// ExtractJSONFromMarkdown returns the contents of the first fenced code block in
// the markdown text md. If there is none, it returns md.
func ExtractJSONFromMarkdown(md string) string {
	// TODO: improve this
	matches := jsonMarkdownRegex.FindStringSubmatch(md)
	if matches == nil {
		return md
	}
	return matches[2]
}

// GetJsonObjectLines splits a string by newlines, trims whitespace from each line,
// and returns a slice containing only the lines that start with '{'.
func GetJsonObjectLines(text string) []string {
	jsonText := ExtractJSONFromMarkdown(text)

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

func ToSchemaMap(config any) map[string]any {
	schema := InferJSONSchema(config)
	result := SchemaAsMap(schema)
	return result
}

// ParsePartialJSON parses potentially incomplete JSON string.
// Based on JS version: js/ai/src/extract.ts parsePartialJson function
// This function attempts to parse partial JSON by fixing common incomplete patterns.
func ParsePartialJSON(jsonString string) (interface{}, error) {
	// Try standard JSON parsing first
	var result interface{}
	if err := json.Unmarshal([]byte(jsonString), &result); err == nil {
		return result, nil
	}

	// Attempt to fix incomplete JSON
	fixed := fixIncompleteJSON(jsonString)
	if err := json.Unmarshal([]byte(fixed), &result); err == nil {
		return result, nil
	}

	return nil, fmt.Errorf("unable to parse partial JSON")
}

// ExtractJSON extracts JSON from string with lenient parsing rules.
// Based on JS version: js/ai/src/extract.ts extractJson function
// It finds JSON objects or arrays in text and extracts them, supporting partial JSON.
func ExtractJSON(text string) (interface{}, error) {
	var openingChar rune
	var closingChar rune
	startPos := -1
	nestingCount := 0
	inString := false
	escapeNext := false

	runes := []rune(text)
	for i := 0; i < len(runes); i++ {
		char := runes[i]

		if escapeNext {
			escapeNext = false
			continue
		}

		if char == '\\' {
			escapeNext = true
			continue
		}

		if char == '"' {
			inString = !inString
			continue
		}

		if inString {
			continue
		}

		if openingChar == 0 && (char == '{' || char == '[') {
			openingChar = char
			if char == '{' {
				closingChar = '}'
			} else {
				closingChar = ']'
			}
			startPos = i
			nestingCount++
		} else if char == openingChar {
			nestingCount++
		} else if char == closingChar {
			nestingCount--
			if nestingCount == 0 {
				// Found complete JSON structure
				jsonStr := string(runes[startPos : i+1])
				var result interface{}
				err := json.Unmarshal([]byte(jsonStr), &result)
				if err == nil {
					return result, nil
				}
				return nil, err
			}
		}
	}

	// If we have an incomplete JSON structure, try to parse it
	if startPos >= 0 && nestingCount > 0 {
		partialJSON := string(runes[startPos:])
		return ParsePartialJSON(partialJSON)
	}

	return nil, fmt.Errorf("no JSON found in text")
}

// ExtractItems extracts JSON array items from text.
// Based on JS version: js/ai/src/extract.ts extractItems
func ExtractItems(text string) []interface{} {
	var items []interface{}
	
	// Try to extract a complete JSON array first
	extracted, err := ExtractJSON(text)
	if err == nil {
		if arr, ok := extracted.([]interface{}); ok {
			return arr
		}
	}
	
	// Look for individual JSON objects in the text
	// This is a simplified version - the JS implementation is more complex
	lines := strings.Split(text, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		
		// Try to parse each line as JSON
		var item interface{}
		if err := json.Unmarshal([]byte(line), &item); err == nil {
			items = append(items, item)
		}
	}
	
	return items
}

// fixIncompleteJSON attempts to fix common patterns of incomplete JSON
func fixIncompleteJSON(input string) string {
	input = strings.TrimSpace(input)

	// Fix incomplete strings first
	input = fixIncompleteStrings(input)

	// Balance braces
	openBraces := strings.Count(input, "{")
	closeBraces := strings.Count(input, "}")
	for i := 0; i < openBraces-closeBraces; i++ {
		input += "}"
	}

	// Balance brackets
	openBrackets := strings.Count(input, "[")
	closeBrackets := strings.Count(input, "]")
	for i := 0; i < openBrackets-closeBrackets; i++ {
		input += "]"
	}

	// Remove trailing commas
	input = strings.ReplaceAll(input, ",}", "}")
	input = strings.ReplaceAll(input, ",]", "]")
	if strings.HasSuffix(input, ",") {
		input = strings.TrimSuffix(input, ",")
	}

	return input
}

// fixIncompleteStrings closes unclosed strings in JSON
func fixIncompleteStrings(input string) string {
	inString := false
	escaped := false
	var result strings.Builder

	for _, ch := range input {
		result.WriteRune(ch)

		if escaped {
			escaped = false
			continue
		}

		if ch == '\\' {
			escaped = true
			continue
		}

		if ch == '"' {
			inString = !inString
		}
	}

	// If still in string, close it
	if inString {
		result.WriteString("\"")
	}

	return result.String()
}
