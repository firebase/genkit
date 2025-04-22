// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0
// Package core provides core functionality for the genkit framework.

package core

import (
	"fmt"
	"sync"
)

// Schema represents a schema definition that can be of any type.
type Schema any

var (
	schemasMu     sync.RWMutex
	schemas       = make(map[string]any)
	schemaLookups []func(string) any
	// Keep track of schemas to register with Dotprompt
	pendingSchemas = make(map[string]Schema)
)

// RegisterSchema registers a schema with the given name.
// This is intended to be called by higher-level packages like ai.
// It validates that the name is not empty and the schema is not nil,
// then registers the schema in the core schemas map.
// Returns the schema for convenience in chaining operations.
func RegisterSchema(name string, schema any) Schema {
	if name == "" {
		panic("core.RegisterSchema: schema name cannot be empty")
	}

	if schema == nil {
		panic("core.RegisterSchema: schema definition cannot be nil")
	}

	schemasMu.Lock()
	defer schemasMu.Unlock()

	if _, exists := schemas[name]; exists {
		panic(fmt.Sprintf("core.RegisterSchema: schema with name %q already exists", name))
	}

	schemas[name] = schema
	pendingSchemas[name] = schema

	return schema
}

// LookupSchema looks up a schema by name.
// It first checks the local registry, and if not found,
// it calls each registered lookup function until one returns a non-nil result.
func LookupSchema(name string) any {
	schemasMu.RLock()
	defer schemasMu.RUnlock()

	// First check local registry
	if schema, ok := schemas[name]; ok {
		return schema
	}

	// Then try lookup functions
	for _, lookup := range schemaLookups {
		if schema := lookup(name); schema != nil {
			return schema
		}
	}

	return nil
}

// RegisterSchemaLookup registers a function that can look up schemas by name.
// This allows different packages to provide schemas while maintaining a
// unified lookup mechanism.
func RegisterSchemaLookup(lookup func(string) any) {
	schemasMu.Lock()
	defer schemasMu.Unlock()

	schemaLookups = append(schemaLookups, lookup)
}

// Schemas returns a copy of all registered schemas.
func Schemas() map[string]any {
	schemasMu.RLock()
	defer schemasMu.RUnlock()

	result := make(map[string]any, len(schemas))
	for name, schema := range schemas {
		result[name] = schema
	}

	return result
}

// ClearSchemas removes all registered schemas.
// This is primarily for testing purposes.
func ClearSchemas() {
	schemasMu.Lock()
	defer schemasMu.Unlock()

	schemas = make(map[string]any)
	pendingSchemas = make(map[string]Schema)
	schemaLookups = nil
}

// PendingSchemas returns a copy of pending schemas that need to be
// registered with Dotprompt.
func PendingSchemas() map[string]Schema {
	schemasMu.RLock()
	defer schemasMu.RUnlock()

	result := make(map[string]Schema, len(pendingSchemas))
	for name, schema := range pendingSchemas {
		result[name] = schema
	}

	return result
}

// ClearPendingSchemas clears the pending schemas map.
// This is called after the schemas have been registered with Dotprompt.
func ClearPendingSchemas() {
	schemasMu.Lock()
	defer schemasMu.Unlock()

	schemas = make(map[string]any)
	pendingSchemas = make(map[string]Schema)
	schemaLookups = nil
}
