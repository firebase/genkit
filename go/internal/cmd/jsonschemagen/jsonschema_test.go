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

package main

import (
	"encoding/json"
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestSchema(t *testing.T) {
	in := `{
      "type": "object",
      "properties": {
        "code": {
          "type": "number"
        },
        "message": {
          "type": "string",
          "additionalProperties": {}
        }
      },
      "required": [
        "code"
      ],
      "additionalProperties": false
    }`
	var got *Schema
	if err := json.Unmarshal([]byte(in), &got); err != nil {
		t.Fatal(err)
	}
	want := &Schema{
		Type: newType("object"),
		Properties: map[string]*Schema{
			"code": &Schema{Type: newType("number")},
			"message": &Schema{
				Type:                 newType("string"),
				AdditionalProperties: &Schema{},
			},
		},
		Required:             []string{"code"},
		AdditionalProperties: &Schema{Not: &Schema{}},
	}

	if diff := cmp.Diff(want, got, cmp.AllowUnexported(OneOf[string, []string]{})); diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}
}

func newType(s string) *OneOf[string, []string] {
	return &OneOf[string, []string]{s}
}
