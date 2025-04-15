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
	"testing"
)

type TestStruct struct {
	Name string
	Age  int
}

func TestDefineAndLookupSchema(t *testing.T) {
	schemaName := "TestStruct"
	testSchema := TestStruct{Name: "Alice", Age: 30}

	// Define the schema
	DefineSchema(schemaName, testSchema)

	// Lookup the schema
	schema, found := LookupSchema(schemaName)
	if !found {
		t.Fatalf("Expected schema '%s' to be found", schemaName)
	}

	// Assert the type
	typedSchema, ok := schema.(TestStruct)
	if !ok {
		t.Fatalf("Expected schema to be of type TestStruct")
	}

	if typedSchema.Name != "Alice" || typedSchema.Age != 30 {
		t.Errorf("Unexpected schema contents: %+v", typedSchema)
	}
}

func TestGetSchemaSuccess(t *testing.T) {
	schemaName := "GetStruct"
	testSchema := TestStruct{Name: "Bob", Age: 25}
	DefineSchema(schemaName, testSchema)

	schema, err := GetSchema(schemaName)
	if err != nil {
		t.Fatalf("Expected schema '%s' to be retrieved without error", schemaName)
	}

	typedSchema := schema.(TestStruct)
	if typedSchema.Name != "Bob" || typedSchema.Age != 25 {
		t.Errorf("Unexpected schema contents: %+v", typedSchema)
	}
}

func TestGetSchemaNotFound(t *testing.T) {
	_, err := GetSchema("NonExistentSchema")
	if err == nil {
		t.Fatal("Expected error when retrieving a non-existent schema")
	}
}

func TestDefineSchemaPanics(t *testing.T) {
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("Expected panic for empty schema name")
		}
	}()
	DefineSchema("", TestStruct{})
}

func TestDefineSchemaNilPanics(t *testing.T) {
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("Expected panic for nil schema")
		}
	}()
	var nilSchema Schema
	DefineSchema("NilSchema", nilSchema)
}
