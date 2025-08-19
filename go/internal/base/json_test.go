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
	"reflect"
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
			want: "foo bar",
		},
		{
			desc: "json markdown",
			in:   "```json{\"a\":1}```",
			want: "{\"a\":1}",
		},
		{
			desc: "json multipline markdown",
			in:   "```json\n{\"a\": 1}\n```",
			want: "\n{\"a\": 1}\n",
		},
		{
			desc: "returns first of multiple blocks",
			in:   "```json{\"a\":\n1}```\n```json\n{\"b\":\n1}```",
			want: "{\"a\":\n1}",
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
		"$id":                  string("https://github.com/firebase/genkit/go/internal/base/foo"),
		"additionalProperties": bool(false),
		"properties": map[string]any{
			"BarField": map[string]any{
				"additionalProperties": bool(false),
				"properties": map[string]any{
					"Bar": map[string]any{"type": string("string")},
				},
				"required": []any{string("Bar")},
				"type":     string("object"),
			},
			"Str": map[string]any{"type": string("string")},
		},
		"required": []any{string("BarField"), string("Str")},
		"type":     string("object"),
	}

	got := SchemaAsMap(InferJSONSchema(Foo{}))
	if diff := cmp.Diff(got, want); diff != "" {
		t.Errorf("SchemaAsMap diff (+got -want):\n%s", diff)
	}
}

func TestParsePartialJSON(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    interface{}
		wantErr bool
	}{
		{
			name:  "complete JSON object",
			input: `{"name": "test", "value": 42}`,
			want:  map[string]interface{}{"name": "test", "value": float64(42)},
		},
		{
			name:  "incomplete JSON object - missing closing brace",
			input: `{"name": "test", "value": 42`,
			want:  map[string]interface{}{"name": "test", "value": float64(42)},
		},
		{
			name:  "incomplete JSON object - missing closing quote",
			input: `{"name": "test`,
			want:  map[string]interface{}{"name": "test"},
		},
		{
			name:  "incomplete JSON array",
			input: `[1, 2, 3`,
			want:  []interface{}{float64(1), float64(2), float64(3)},
		},
		{
			name:  "nested incomplete JSON",
			input: `{"data": {"nested": true`,
			want:  map[string]interface{}{"data": map[string]interface{}{"nested": true}},
		},
		{
			name:  "trailing comma",
			input: `{"name": "test",}`,
			want:  map[string]interface{}{"name": "test"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParsePartialJSON(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("ParsePartialJSON() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !tt.wantErr && !reflect.DeepEqual(got, tt.want) {
				t.Errorf("ParsePartialJSON() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestExtractJSON(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    interface{}
		wantErr bool
	}{
		{
			name:  "JSON object in text",
			input: `Some text before {"name": "test", "value": 42} and after`,
			want:  map[string]interface{}{"name": "test", "value": float64(42)},
		},
		{
			name:  "JSON array in text",
			input: `Result: [1, 2, 3] done`,
			want:  []interface{}{float64(1), float64(2), float64(3)},
		},
		{
			name:  "incomplete JSON with text",
			input: `Generating: {"status": "processing", "progress": 50`,
			want:  map[string]interface{}{"status": "processing", "progress": float64(50)},
		},
		{
			name:    "no JSON in text",
			input:   `Just plain text without any JSON`,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ExtractJSON(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("ExtractJSON() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !tt.wantErr && !reflect.DeepEqual(got, tt.want) {
				t.Errorf("ExtractJSON() = %v, want %v", got, tt.want)
			}
		})
	}
}
