// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0


package base

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/invopop/jsonschema"
	"github.com/xeipuuv/gojsonschema"
)

// ValidateValue will validate any value against the expected schema.
// It will return an error if it doesn't match the schema, otherwise it will return nil.
func ValidateValue(data any, schema *jsonschema.Schema) error {
	dataBytes, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("data is not a valid JSON type: %w", err)
	}
	return ValidateJSON(dataBytes, schema)
}

// ValidateJSON will validate JSON against the expected schema.
// It will return an error if it doesn't match the schema, otherwise it will return nil.
func ValidateJSON(dataBytes json.RawMessage, schema *jsonschema.Schema) error {
	schemaBytes, err := schema.MarshalJSON()
	if err != nil {
		return fmt.Errorf("expected schema is not valid: %w", err)
	}
	return ValidateRaw(dataBytes, schemaBytes)
}

// ValidateRaw will validate JSON data against the JSON schema.
// It will return an error if it doesn't match the schema, otherwise it will return nil.
func ValidateRaw(dataBytes json.RawMessage, schemaBytes json.RawMessage) error {
	var data any
	// Do this check separately from below to get a better error message.
	if err := json.Unmarshal(dataBytes, &data); err != nil {
		return fmt.Errorf("data is not valid JSON: %w", err)
	}

	schemaLoader := gojsonschema.NewBytesLoader(schemaBytes)
	documentLoader := gojsonschema.NewBytesLoader(dataBytes)

	result, err := gojsonschema.Validate(schemaLoader, documentLoader)
	if err != nil {
		return fmt.Errorf("failed to validate data against expected schema: %w", err)
	}

	if !result.Valid() {
		var errors []string
		for _, err := range result.Errors() {
			errors = append(errors, fmt.Sprintf("- %s", err))
		}
		return fmt.Errorf("data did not match expected schema:\n%s", strings.Join(errors, "\n"))
	}

	return nil
}
