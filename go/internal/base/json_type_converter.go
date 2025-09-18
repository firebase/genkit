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
//
// SPDX-License-Identifier: Apache-2.0

package base

import (
	"fmt"
)

// NormalizeInput recursively traverses a data structure and performs normalization:
// 1. Removes any fields with null values
// 2. Converts instances of float64 into int64 or float64 based on the schema's "type" property
func NormalizeInput(data any, schema map[string]any) (any, error) {
	if data == nil {
		return data, nil
	}

	switch d := data.(type) {
	case float64:
		return convertFloat64(d, schema)
	case map[string]any:
		return normalizeObjectInput(d, schema)
	case []any:
		return normalizeArrayInput(d, schema)
	default:
		return data, nil
	}
}

// convertFloat64 converts a float64 to an int64 or float64 based on the schema's "type" property.
func convertFloat64(f float64, schema map[string]any) (any, error) {
	schemaType, ok := schema["type"].(string)
	if !ok {
		return f, nil // No type specified, leave as float64
	}

	switch schemaType {
	case "integer":
		// Convert float64 to int64 if it represents a whole number
		if f == float64(int64(f)) {
			return int64(f), nil
		}
		return nil, fmt.Errorf("cannot convert %f to integer: not a whole number", f)
	case "number":
		return f, nil // Already a float64
	default:
		return f, nil // Not a numeric type, leave as is
	}
}

// normalizeObjectInput normalizes map values by removing null fields and converting JSON numbers.
func normalizeObjectInput(obj map[string]any, schema map[string]any) (map[string]any, error) {
	var props map[string]any
	if schema != nil {
		props, _ = schema["properties"].(map[string]any)
	}

	// If no schema or no properties, just remove null fields and normalize recursively
	if schema == nil || props == nil {
		newObj := make(map[string]any)
		for k, v := range obj {
			if v != nil {
				normalized, err := NormalizeInput(v, nil)
				if err != nil {
					return nil, err
				}
				newObj[k] = normalized
			}
		}
		return newObj, nil
	}

	newObj := make(map[string]any)
	for k, v := range obj {
		// Skip null values - this removes the field entirely
		if v == nil {
			continue
		}

		propSchema, ok := props[k].(map[string]any)
		if !ok {
			// No schema for this property, just keep it if not null
			normalized, err := NormalizeInput(v, nil)
			if err != nil {
				return nil, err
			}
			newObj[k] = normalized
			continue
		}

		normalized, err := NormalizeInput(v, propSchema)
		if err != nil {
			return nil, err
		}
		newObj[k] = normalized
	}
	return newObj, nil
}

// normalizeArrayInput normalizes array values by converting JSON numbers and handling null elements.
func normalizeArrayInput(arr []any, schema map[string]any) ([]any, error) {
	items, ok := schema["items"].(map[string]any)
	if !ok {
		// No items schema, just normalize each element
		newArr := make([]any, len(arr))
		for i, v := range arr {
			normalized, err := NormalizeInput(v, nil)
			if err != nil {
				return nil, err
			}
			newArr[i] = normalized
		}
		return newArr, nil
	}

	newArr := make([]any, len(arr))
	for i, v := range arr {
		normalized, err := NormalizeInput(v, items)
		if err != nil {
			return nil, err
		}
		newArr[i] = normalized
	}
	return newArr, nil
}
