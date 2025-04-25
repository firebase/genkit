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
package core

import (
	"fmt"
	"reflect"
	"sync"
	"testing"
)

// clearSchemasForTest removes all registered schemas.
// This is exclusively for testing purposes.
func clearSchemasForTest() {
	schemasMu.Lock()
	defer schemasMu.Unlock()

	schemas = make(map[string]any)
	pendingSchemas = make(map[string]Schema)
	schemaLookups = nil
}

// TestRegisterSchema tests schema registration functionality
func TestRegisterSchema(t *testing.T) {
	clearSchemasForTest()
	t.Cleanup(clearSchemasForTest)

	t.Run("RegisterValidSchema", func(t *testing.T) {
		schema := map[string]interface{}{"type": "object"}
		result, err := RegisterSchema("test", schema)

		if err != nil {
			t.Fatalf("Unexpected error: %v", err)
		}

		if result == nil {
			t.Fatal("Expected RegisterSchema to return the schema, got nil")
		}

		retrieved := LookupSchema("test")
		if retrieved == nil {
			t.Fatal("Failed to retrieve registered schema")
		}

		if !reflect.DeepEqual(retrieved, schema) {
			t.Fatalf("Retrieved schema doesn't match registered schema. Got %v, want %v", retrieved, schema)
		}
	})

	t.Run("RegisterDuplicateName", func(t *testing.T) {
		clearSchemasForTest()
		_, err := RegisterSchema("duplicate", "first")
		if err != nil {
			t.Fatalf("Unexpected error registering first schema: %v", err)
		}

		_, err = RegisterSchema("duplicate", "second")
		if err == nil {
			t.Fatal("Expected error when registering duplicate schema name, but no error occurred")
		}
		expectedErrMsg := `core.RegisterSchema: schema with name "duplicate" already exists`
		if err.Error() != expectedErrMsg {
			t.Fatalf("Expected error message %q, got %q", expectedErrMsg, err.Error())
		}
	})

	t.Run("RegisterEmptyName", func(t *testing.T) {
		_, err := RegisterSchema("", "schema")
		if err == nil {
			t.Fatal("Expected error when registering schema with empty name, but no error occurred")
		}
		expectedErrMsg := "core.RegisterSchema: schema name cannot be empty"
		if err.Error() != expectedErrMsg {
			t.Fatalf("Expected error message %q, got %q", expectedErrMsg, err.Error())
		}
	})

	t.Run("RegisterNilSchema", func(t *testing.T) {
		_, err := RegisterSchema("nil_schema", nil)
		if err == nil {
			t.Fatal("Expected error when registering nil schema, but no error occurred")
		}
		expectedErrMsg := "core.RegisterSchema: schema definition cannot be nil"
		if err.Error() != expectedErrMsg {
			t.Fatalf("Expected error message %q, got %q", expectedErrMsg, err.Error())
		}
	})
}

// TestLookupSchema tests schema lookup functionality
func TestLookupSchema(t *testing.T) {
	clearSchemasForTest()
	t.Cleanup(clearSchemasForTest)

	t.Run("LookupExistingSchema", func(t *testing.T) {
		expectedSchema := "test_schema"
		_, err := RegisterSchema("existing", expectedSchema)
		if err != nil {
			t.Fatalf("Failed to register schema: %v", err)
		}

		result := LookupSchema("existing")
		if result != expectedSchema {
			t.Fatalf("Expected schema %v, got %v", expectedSchema, result)
		}
	})

	t.Run("LookupNonExistentSchema", func(t *testing.T) {
		result := LookupSchema("nonexistent")
		if result != nil {
			t.Fatalf("Expected nil for non-existent schema, got %v", result)
		}
	})

	t.Run("LookupViaCustomFunction", func(t *testing.T) {
		expectedSchema := "custom_schema"
		RegisterSchemaLookup(func(name string) any {
			if name == "custom" {
				return expectedSchema
			}
			return nil
		})

		result := LookupSchema("custom")
		if result != expectedSchema {
			t.Fatalf("Expected schema %v from custom lookup, got %v", expectedSchema, result)
		}
	})

	t.Run("PreferLocalRegistryOverLookup", func(t *testing.T) {
		localSchema := "local_schema"
		_, err := RegisterSchema("preference_test", localSchema)
		if err != nil {
			t.Fatalf("Failed to register schema: %v", err)
		}

		lookupSchema := "lookup_schema"
		RegisterSchemaLookup(func(name string) any {
			if name == "preference_test" {
				return lookupSchema
			}
			return nil
		})

		result := LookupSchema("preference_test")
		if result != localSchema {
			t.Fatalf("Expected local schema %v to be preferred, got %v", localSchema, result)
		}
	})
}

// TestPendingSchemas tests handling of pending schemas
func TestPendingSchemas(t *testing.T) {
	clearSchemasForTest()
	t.Cleanup(clearSchemasForTest)

	t.Run("GetPendingSchemas", func(t *testing.T) {
		_, err := RegisterSchema("pending1", "test1")
		if err != nil {
			t.Fatalf("Failed to register first schema: %v", err)
		}

		_, err = RegisterSchema("pending2", "test2")
		if err != nil {
			t.Fatalf("Failed to register second schema: %v", err)
		}

		pending := PendingSchemas()
		if len(pending) != 2 {
			t.Fatalf("Expected 2 pending schemas, got %d", len(pending))
		}

		if pending["pending1"] != "test1" || pending["pending2"] != "test2" {
			t.Fatal("Pending schemas don't match expected values")
		}
	})

	t.Run("ClearPendingSchemas", func(t *testing.T) {
		_, err := RegisterSchema("pending3", "test3")
		if err != nil {
			t.Fatalf("Failed to register schema: %v", err)
		}

		ClearPendingSchemas()

		pending := PendingSchemas()
		if len(pending) != 0 {
			t.Fatalf("Expected 0 pending schemas after clearing, got %d", len(pending))
		}
	})
}

// TestSchemas tests the Schemas function that returns all registered schemas
func TestSchemas(t *testing.T) {
	clearSchemasForTest()
	t.Cleanup(clearSchemasForTest)

	_, err := RegisterSchema("schema1", "value1")
	if err != nil {
		t.Fatalf("Failed to register first schema: %v", err)
	}

	_, err = RegisterSchema("schema2", "value2")
	if err != nil {
		t.Fatalf("Failed to register second schema: %v", err)
	}

	schemasMap := Schemas()
	if len(schemasMap) != 2 {
		t.Fatalf("Expected 2 schemas, got %d", len(schemasMap))
	}

	if schemasMap["schema1"] != "value1" || schemasMap["schema2"] != "value2" {
		t.Fatal("Retrieved schemas don't match expected values")
	}

	schemasMap["schema3"] = "value3"

	internalSchemas := Schemas()
	if len(internalSchemas) != 2 {
		t.Fatalf("Expected internal schemas count to remain 2, got %d", len(internalSchemas))
	}

	if _, exists := internalSchemas["schema3"]; exists {
		t.Fatal("Modifying returned schemas map should not affect internal state")
	}
}

// TestConcurrentAccess tests thread safety of schema operations
func TestConcurrentAccess(t *testing.T) {
	clearSchemasForTest()
	t.Cleanup(clearSchemasForTest)

	const numGoroutines = 10
	const schemasPerGoroutine = 100

	var wg sync.WaitGroup
	wg.Add(numGoroutines)

	for i := 0; i < numGoroutines; i++ {
		go func(routineID int) {
			defer wg.Done()

			for j := 0; j < schemasPerGoroutine; j++ {
				name := fmt.Sprintf("schema_r%d_s%d", routineID, j)
				_, err := RegisterSchema(name, j)
				if err != nil {
					t.Errorf("Unexpected error registering schema %s: %v", name, err)
				}
			}

			for j := 0; j < schemasPerGoroutine; j++ {
				name := fmt.Sprintf("schema_r%d_s%d", routineID, j)
				value := LookupSchema(name)
				if value != j {
					t.Errorf("Expected schema value %d for %s, got %v", j, name, value)
				}
			}
		}(i)
	}

	wg.Wait()

	schemasMap := Schemas()
	expectedCount := numGoroutines * schemasPerGoroutine
	if len(schemasMap) != expectedCount {
		t.Fatalf("Expected %d total schemas, got %d", expectedCount, len(schemasMap))
	}
}
