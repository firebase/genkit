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

package core

import (
	"encoding/json"
	"fmt"

	"github.com/invopop/jsonschema"
	"github.com/xeipuuv/gojsonschema"
)

// ValidateObject will validate any object against the expected schema.
// It will return an error if it doesn't match the schema, otherwise it will return nil.
func ValidateObject(data any, schema *jsonschema.Schema) error {
	dataBytes, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("object is not a valid JSON type: %w", err)
	}
	return ValidateJSON(dataBytes, schema)
}

// ValidateJSON will validate JSON against the expected schema.
// It will return an error if it doesn't match the schema, otherwise it will return nil.
func ValidateJSON(dataBytes json.RawMessage, schema *jsonschema.Schema) error {
	schemaBytes, err := schema.MarshalJSON()
	if err != nil {
		return fmt.Errorf("schema is not valid: %w", err)
	}
	return ValidateRaw(dataBytes, schemaBytes)
}

// ValidateRaw will validate JSON data against the JSON schema.
// It will return an error if it doesn't match the schema, otherwise it will return nil.
func ValidateRaw(dataBytes json.RawMessage, schemaBytes json.RawMessage) error {
	schemaLoader := gojsonschema.NewBytesLoader(schemaBytes)
	documentLoader := gojsonschema.NewBytesLoader(dataBytes)

	result, err := gojsonschema.Validate(schemaLoader, documentLoader)
	if err != nil {
		return err
	}

	if !result.Valid() {
		var errors string
		for _, err := range result.Errors() {
			errors += fmt.Sprintf("- %s\n", err)
		}
		return fmt.Errorf("data did not match the schema:\n%s", errors)
	}

	return nil
}
