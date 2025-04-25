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

package genkit

import (
	"fmt"
	"log/slog"
	"sync"

	"github.com/firebase/genkit/go/core"
	"github.com/google/dotprompt/go/dotprompt"
	"github.com/invopop/jsonschema"
)

// Schema is an alias for core.Schema to maintain compatibility with existing type definitions
type Schema = core.Schema

// schemasMu and pendingSchemas are maintained for backward compatibility
var (
	schemasMu      sync.RWMutex
	pendingSchemas = make(map[string]Schema)
)

// DefineSchema registers a schema that can be referenced by name in genkit.
// This allows schemas to be defined once and used across the AI generation pipeline.
//
// Example usage:
//
//	type Person struct {
//	    Name string `json:"name"`
//	    Age  int    `json:"age"`
//	}
//
//	personSchema := genkit.DefineSchema("Person", Person{})
func DefineSchema(name string, schema Schema) (Schema, error) {
	if name == "" {
		return nil, fmt.Errorf("genkit.DefineSchema: schema name cannot be empty")
	}

	if schema == nil {
		return nil, fmt.Errorf("genkit.DefineSchema: schema cannot be nil")
	}

	core.RegisterSchema(name, schema)

	schemasMu.Lock()
	defer schemasMu.Unlock()
	pendingSchemas[name] = schema

	return schema, nil
}

// LookupSchema retrieves a registered schema by name.
// It returns nil and false if no schema exists with that name.
func LookupSchema(name string) (Schema, bool) {
	schema := core.LookupSchema(name)
	return schema, schema != nil
}

// FindSchema retrieves a registered schema by name.
// It returns an error if no schema exists with that name.
func FindSchema(name string) (Schema, error) {
	schema, exists := LookupSchema(name)
	if !exists {
		return nil, fmt.Errorf("genkit: schema '%s' not found", name)
	}
	return schema, nil
}

// registerSchemaResolver registers a schema resolver with Dotprompt to handle schema lookups
func registerSchemaResolver(dp *dotprompt.Dotprompt) {
	// Create a schema resolver that can look up schemas from the Genkit registry
	schemaResolver := func(name string) any {
		schema, exists := LookupSchema(name)
		if !exists {
			slog.Error("schema not found in registry", "name", name)
			return nil
		}

		reflector := jsonschema.Reflector{}
		jsonSchema := reflector.Reflect(schema)
		return jsonSchema
	}

	dp.RegisterExternalSchemaLookup(schemaResolver)
}

// RegisterGlobalSchemaResolver exports the schema lookup capabilities for use in other packages
func RegisterGlobalSchemaResolver(dp *dotprompt.Dotprompt) {
	dp.RegisterExternalSchemaLookup(func(name string) any {
		schema, exists := LookupSchema(name)
		if !exists {
			return nil
		}

		reflector := jsonschema.Reflector{}
		jsonSchema := reflector.Reflect(schema)
		return jsonSchema
	})
}
