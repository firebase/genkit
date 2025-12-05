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

package base

import (
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestExtractJSONFromMarkdown(t *testing.T) {
	tests := []struct {
		desc string
		in   string
		want string
	}{
		{
			desc: "no markdown",
			in:   "abcdefg",
			want: "abcdefg",
		},
		{
			desc: "no markdown (with line breaks)",
			in:   "ab\ncd\nfg",
			want: "ab\ncd\nfg",
		},
		{
			desc: "simple markdown",
			in:   "```foo bar```",
			want: "```foo bar```",
		},
		{
			desc: "empty markdown",
			in:   "``` ```",
			want: "``` ```",
		},
		{
			desc: "json markdown",
			in:   "```json{\"a\":1}```",
			want: "{\"a\":1}",
		},
		{
			desc: "json multiple line markdown",
			in:   "```json\n{\"a\": 1}\n```",
			want: "{\"a\": 1}",
		},
		{
			desc: "returns first of multiple blocks",
			in:   "```json{\"a\":\n1}```\n```json\n{\"b\":\n1}```",
			want: "{\"a\":\n1}",
		},
		{
			desc: "yaml markdown",
			in:   "```yaml\nkey: 1\nanother-key: 2```",
			want: "```yaml\nkey: 1\nanother-key: 2```",
		},
		{
			desc: "yaml + json markdown",
			in:   "```yaml\nkey: 1\nanother-key: 2``` ```json\n{\"a\": 1}\n```",
			want: "{\"a\": 1}",
		},
		{
			desc: "json + yaml markdown",
			in:   "```json\n{\"a\": 1}\n``` ```yaml\nkey: 1\nanother-key: 2```",
			want: "{\"a\": 1}",
		},
	}
	for _, tc := range tests {
		t.Run(tc.desc, func(t *testing.T) {
			if diff := cmp.Diff(ExtractJSONFromMarkdown(tc.in), tc.want); diff != "" {
				t.Errorf("ExtractJSONFromMarkdown diff (+got -want):\n%s", diff)
			}
		})
	}
}

func TestSchemaAsMap(t *testing.T) {
	type Bar struct {
		Bar string
	}
	type Foo struct {
		BarField Bar
		Str      string
	}

	want := map[string]any{
		"$defs": map[string]any{
			"Bar": map[string]any{
				"additionalProperties": bool(false),
				"properties": map[string]any{
					"Bar": map[string]any{"type": string("string")},
				},
				"required": []any{string("Bar")},
				"type":     string("object"),
			},
			"Foo": map[string]any{
				"additionalProperties": bool(false),
				"properties": map[string]any{
					"BarField": map[string]any{
						"$ref": string("#/$defs/Bar"),
					},
					"Str": map[string]any{"type": string("string")},
				},
				"required": []any{string("BarField"), string("Str")},
				"type":     string("object"),
			},
		},
		"$ref": string("#/$defs/Foo"),
	}

	got := SchemaAsMap(InferJSONSchema(Foo{}))
	if diff := cmp.Diff(got, want); diff != "" {
		t.Errorf("SchemaAsMap diff (+got -want):\n%s", diff)
	}
}

func TestSchemaAsMapRecursive(t *testing.T) {
	type Node struct {
		Value    string  `json:"value,omitempty"`
		Children []*Node `json:"children,omitempty"`
	}

	schema := SchemaAsMap(InferJSONSchema(Node{}))

	defs, ok := schema["$defs"].(map[string]any)
	if !ok {
		t.Fatal("expected $defs in schema")
	}

	if _, ok := defs["Node"]; !ok {
		t.Error("expected Node in $defs")
	}

	if ref, ok := schema["$ref"].(string); !ok || ref != "#/$defs/Node" {
		t.Errorf("expected $ref to be #/$defs/Node, got %v", schema["$ref"])
	}

	nodeDef, ok := defs["Node"].(map[string]any)
	if !ok {
		t.Fatal("expected Node definition to be a map")
	}
	nodeProps, ok := nodeDef["properties"].(map[string]any)
	if !ok {
		t.Fatal("expected Node to have properties")
	}
	childrenField, ok := nodeProps["children"].(map[string]any)
	if !ok {
		t.Fatal("expected Node to have children field")
	}
	items, ok := childrenField["items"].(map[string]any)
	if !ok {
		t.Fatal("expected children to have items")
	}
	if ref, ok := items["$ref"].(string); !ok || ref != "#/$defs/Node" {
		t.Errorf("expected children.items to reference Node, got %v", items)
	}
}
