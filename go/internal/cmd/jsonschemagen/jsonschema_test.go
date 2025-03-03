// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

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
