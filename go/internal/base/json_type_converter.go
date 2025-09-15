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

// ConvertJSONNumbers recursively traverses a data structure and a corresponding JSON schema.
// It converts instances of float64 into int64 or float64 based on the schema's "type" property.
func ConvertJSONNumbers(data any, schema map[string]any) (any, error) {
	if data == nil || schema == nil {
		return data, nil
	}

	switch d := data.(type) {
	case float64:
		return convertFloat64(d, schema)
	case map[string]any:
		return convertObjectNumbers(d, schema)
	case []any:
		return convertArrayNumbers(d, schema)
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

// convertObjectNumbers converts any float64s in the map values to int64 or float64 based on the schema's "type" property.
func convertObjectNumbers(obj map[string]any, schema map[string]any) (map[string]any, error) {
	props, ok := schema["properties"].(map[string]any)
	if !ok {
		return obj, nil // No properties to guide conversion
	}

	newObj := make(map[string]any, len(obj))
	for k, v := range obj {
		newObj[k] = v // Copy original value

		propSchema, ok := props[k].(map[string]any)
		if !ok {
			continue // No schema for this property
		}

		converted, err := ConvertJSONNumbers(v, propSchema)
		if err != nil {
			return nil, err
		}
		newObj[k] = converted
	}
	return newObj, nil
}

// convertArrayNumbers converts any float64s in the array values to int64 or float64 based on the schema's "type" property.
func convertArrayNumbers(arr []any, schema map[string]any) ([]any, error) {
	items, ok := schema["items"].(map[string]any)
	if !ok {
		return arr, nil // No items schema to guide conversion
	}

	newArr := make([]any, len(arr))
	for i, v := range arr {
		converted, err := ConvertJSONNumbers(v, items)
		if err != nil {
			return nil, err
		}
		newArr[i] = converted
	}
	return newArr, nil
}
