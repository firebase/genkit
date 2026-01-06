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
	"context"
	"testing"

	"github.com/firebase/genkit/go/core"
)

func TestStreamFlow(t *testing.T) {
	g := Init(context.Background())

	f := DefineStreamingFlow(g, "count", count)
	iter := f.Stream(context.Background(), 2)
	want := 0
	iter(func(val *core.StreamingFlowValue[int, int], err error) bool {
		if err != nil {
			t.Fatal(err)
		}
		var got int
		if val.Done {
			got = val.Output
		} else {
			got = val.Stream
		}
		if got != want {
			t.Errorf("got %d, want %d", got, want)
		}
		want++
		return true
	})
}

// count streams the numbers from 0 to n-1, then returns n.
func count(ctx context.Context, n int, cb func(context.Context, int) error) (int, error) {
	if cb != nil {
		for i := range n {
			if err := cb(ctx, i); err != nil {
				return 0, err
			}
		}
	}
	return n, nil
}

func TestDefineSchemaWithType(t *testing.T) {
	g := Init(context.Background())

	type UserInfo struct {
		Name string `json:"name"`
		Age  int    `json:"age,omitempty"`
	}

	DefineSchemaFor[UserInfo](g)

	schema := g.reg.LookupSchema("UserInfo")
	if schema == nil {
		t.Fatal("Schema UserInfo not found")
	}

	if schema["type"] != "object" {
		t.Errorf("Expected type object, got %v", schema["type"])
	}

	props, ok := schema["properties"].(map[string]any)
	if !ok {
		t.Fatal("Properties not found or invalid type")
	}

	if _, ok := props["name"]; !ok {
		t.Error("Property 'name' not found")
	}
	if _, ok := props["age"]; !ok {
		t.Error("Property 'age' not found")
	}

	required, ok := schema["required"].([]any)
	if !ok {
		t.Fatal("Required fields not found or invalid type")
	}
	// jsonschema reflection makes fields required by default unless omitempty
	foundName := false
	for _, r := range required {
		if r == "name" {
			foundName = true
			break
		}
	}
	if !foundName {
		t.Error("Expected 'name' to be required")
	}
}

func TestDefineSchemaWithType_Error(t *testing.T) {
	g := Init(context.Background())

	// We expect a panic because DefineSchemaWithType panics on error
	defer func() {
		if r := recover(); r == nil {
			t.Errorf("The code did not panic")
		}
	}()

	type Invalid struct {
		Foo func() `json:"foo"`
	}

	DefineSchemaFor[Invalid](g)
}
