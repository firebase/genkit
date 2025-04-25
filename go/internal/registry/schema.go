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

package registry

import (
	"fmt"
	"reflect"
	"strings"

	"github.com/google/dotprompt/go/dotprompt"
	"github.com/invopop/jsonschema"
	orderedmap "github.com/wk8/go-ordered-map/v2"
)

// DefineSchema registers a Go struct as a schema with the given name.
func (r *Registry) DefineSchema(name string, structType any) error {
	jsonSchema, err := convertStructToJsonSchema(structType)
	if err != nil {
		return err
	}

	if r.Dotprompt == nil {
		r.Dotprompt = dotprompt.NewDotprompt(&dotprompt.DotpromptOptions{
			Schemas: map[string]*jsonschema.Schema{},
		})
	}

	r.Dotprompt.DefineSchema(name, jsonSchema)
	r.RegisterValue(SchemaType+"/"+name, structType)
	fmt.Printf("Registered schema '%s' with registry and Dotprompt\n", name)
	return nil
}

// RegisterSchemaWithDotprompt registers a schema with the Dotprompt instance
// This is used during Init to register schemas that were defined before the registry was created.
func (r *Registry) RegisterSchemaWithDotprompt(name string, schema any) error {
	if r.Dotprompt == nil {
		r.Dotprompt = dotprompt.NewDotprompt(&dotprompt.DotpromptOptions{
			Schemas: map[string]*jsonschema.Schema{},
		})
	}

	jsonSchema, err := convertStructToJsonSchema(schema)
	if err != nil {
		return err
	}

	r.Dotprompt.DefineSchema(name, jsonSchema)
	r.RegisterValue(SchemaType+"/"+name, schema)

	// Set up schema lookup if not already done
	r.setupSchemaLookupFunction()

	return nil
}

// setupSchemaLookupFunction registers the external schema lookup function with Dotprompt
// This function bridges between Dotprompt's schema resolution and the registry's values
func (r *Registry) setupSchemaLookupFunction() {
	if r.Dotprompt == nil {
		return
	}

	r.Dotprompt.RegisterExternalSchemaLookup(func(schemaName string) any {
		schemaValue := r.LookupValue(SchemaType + "/" + schemaName)
		if schemaValue != nil {
			return schemaValue
		}
		return nil
	})
}

// convertStructToJsonSchema converts a Go struct to a JSON schema
func convertStructToJsonSchema(structType any) (*jsonschema.Schema, error) {
	t := reflect.TypeOf(structType)
	if t.Kind() == reflect.Ptr {
		t = t.Elem()
	}

	if t.Kind() != reflect.Struct {
		return nil, fmt.Errorf("expected struct type, got %s", t.Kind())
	}

	schema := &jsonschema.Schema{
		Type:       "object",
		Properties: orderedmap.New[string, *jsonschema.Schema](),
		Required:   []string{},
	}

	for i := 0; i < t.NumField(); i++ {
		field := t.Field(i)

		if field.PkgPath != "" {
			continue
		}

		jsonTag := field.Tag.Get("json")
		parts := strings.Split(jsonTag, ",")
		propName := parts[0]
		if propName == "" {
			propName = field.Name
		}

		if propName == "-" {
			continue
		}

		isRequired := true
		for _, opt := range parts[1:] {
			if opt == "omitempty" {
				isRequired = false
				break
			}
		}

		if isRequired {
			schema.Required = append(schema.Required, propName)
		}

		description := field.Tag.Get("description")

		fieldSchema := fieldToSchema(field.Type, description)
		schema.Properties.Set(propName, fieldSchema)
	}

	return schema, nil
}

// fieldToSchema converts a field type to a JSON Schema.
func fieldToSchema(t reflect.Type, description string) *jsonschema.Schema {
	schema := &jsonschema.Schema{}

	if description != "" {
		schema.Description = description
	}

	if t.Kind() == reflect.Ptr {
		t = t.Elem()
	}

	switch t.Kind() {
	case reflect.String:
		schema.Type = "string"
	case reflect.Bool:
		schema.Type = "boolean"
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
		reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		schema.Type = "integer"
	case reflect.Float32, reflect.Float64:
		schema.Type = "number"
	case reflect.Slice, reflect.Array:
		schema.Type = "array"
		itemSchema := fieldToSchema(t.Elem(), "")
		schema.Items = itemSchema
	case reflect.Map:
		schema.Type = "object"
		if t.Key().Kind() == reflect.String {
			valueSchema := fieldToSchema(t.Elem(), "")
			schema.AdditionalProperties = valueSchema
		}
	case reflect.Struct:
		schema.Type = "object"
		schema.Properties = orderedmap.New[string, *jsonschema.Schema]()
		schema.Required = []string{}

		for i := 0; i < t.NumField(); i++ {
			field := t.Field(i)

			if field.PkgPath != "" {
				continue
			}

			jsonTag := field.Tag.Get("json")
			parts := strings.Split(jsonTag, ",")
			propName := parts[0]
			if propName == "" {
				propName = field.Name
			}

			if propName == "-" {
				continue
			}

			isRequired := true
			for _, opt := range parts[1:] {
				if opt == "omitempty" {
					isRequired = false
					break
				}
			}

			if isRequired {
				schema.Required = append(schema.Required, propName)
			}

			fieldDescription := field.Tag.Get("description")

			fieldSchema := fieldToSchema(field.Type, fieldDescription)
			schema.Properties.Set(propName, fieldSchema)
		}
	default:
		schema.Type = "string"
	}

	return schema
}
