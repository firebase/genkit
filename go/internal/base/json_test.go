// Copyright 2024 Google LLC
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

	got := SchemaAsMap(InferJSONSchemaNonReferencing(Foo{}))
	if diff := cmp.Diff(got, want); diff != "" {
		t.Errorf("SchemaAsMap diff (+got -want):\n%s", diff)
	}
}
