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
	if !p.IsPlainText() {
		t.Errorf("IsPlainText() == %t, want %t", p.IsPlainText(), true)
	}
	if got := p.Text(); got != data {
		t.Errorf("Data() == %q, want %q", got, data)
	}
}

// TODO(iant): verify that this works with the data that genkit passes.
func TestDocumentJSON(t *testing.T) {
	d := Document{
		Content: []*Part{
			&Part{
				kind: partText,
				text: "hi",
			},
			&Part{
				kind:        partBlob,
				contentType: "text/plain",
				text:        "data:,bye",
			},
			&Part{
				kind: partToolRequest,
				toolRequest: &ToolRequest{
					Name:  "tool1",
					Input: map[string]any{"arg1": 3.3, "arg2": "foo"},
				},
			},
			&Part{
				kind: partToolResponse,
				toolResponse: &ToolResponse{
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
		if a.kind != b.kind {
			return false
		}
		switch a.kind {
		case partText:
			return a.text == b.text
		case partBlob:
			return a.contentType == b.contentType && a.text == b.text
		case partToolRequest:
			return reflect.DeepEqual(a.toolRequest, b.toolRequest)
		case partToolResponse:
			return reflect.DeepEqual(a.toolResponse, b.toolResponse)
		default:
			t.Fatalf("bad part kind %v", a.kind)
			return false
		}
	}

	diff := cmp.Diff(d, d2, cmp.Comparer(cmpPart))
	if diff != "" {
		t.Errorf("mismatch (-want, +got)\n%s", diff)
	}
}
