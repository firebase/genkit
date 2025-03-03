// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"encoding/json"
	"reflect"
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestDocumentFromText(t *testing.T) {
	const data = "robot overlord"
	d := DocumentFromText(data, nil)
	if len(d.Content) != 1 {
		t.Fatalf("got %d parts, want 1", len(d.Content))
	}
	p := d.Content[0]
	if !p.IsText() {
		t.Errorf("IsText() == %t, want %t", p.IsText(), true)
	}
	if got := p.Text; got != data {
		t.Errorf("Data() == %q, want %q", got, data)
	}
}

// TODO: verify that this works with the data that genkit passes.
func TestDocumentJSON(t *testing.T) {
	d := Document{
		Content: []*Part{
			&Part{
				Kind: PartText,
				Text: "hi",
			},
			&Part{
				Kind:        PartMedia,
				ContentType: "text/plain",
				Text:        "data:,bye",
			},
			&Part{
				Kind: PartData,
				Text: "somedata\x00string",
			},
			&Part{
				Kind: PartToolRequest,
				ToolRequest: &ToolRequest{
					Name:  "tool1",
					Input: map[string]any{"arg1": 3.3, "arg2": "foo"},
				},
			},
			&Part{
				Kind: PartToolResponse,
				ToolResponse: &ToolResponse{
					Name:   "tool1",
					Output: map[string]any{"res1": 4.4, "res2": "bar"},
				},
			},
		},
	}

	b, err := json.Marshal(&d)
	if err != nil {
		t.Fatal(err)
	}
	t.Logf("marshaled:%s\n", string(b))

	var d2 Document
	if err := json.Unmarshal(b, &d2); err != nil {
		t.Fatal(err)
	}

	cmpPart := func(a, b *Part) bool {
		if a.Kind != b.Kind {
			return false
		}
		switch a.Kind {
		case PartText:
			return a.Text == b.Text
		case PartMedia:
			return a.ContentType == b.ContentType && a.Text == b.Text
		case PartData:
			return a.Text == b.Text
		case PartToolRequest:
			return reflect.DeepEqual(a.ToolRequest, b.ToolRequest)
		case PartToolResponse:
			return reflect.DeepEqual(a.ToolResponse, b.ToolResponse)
		default:
			t.Fatalf("bad part kind %v", a.Kind)
			return false
		}
	}

	diff := cmp.Diff(d, d2, cmp.Comparer(cmpPart))
	if diff != "" {
		t.Errorf("mismatch (-want, +got)\n%s", diff)
	}
}
