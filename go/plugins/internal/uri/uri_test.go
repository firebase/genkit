// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package uri

import (
	"testing"

	"github.com/firebase/genkit/go/ai"
)

func TestData(t *testing.T) {
	tests := []struct {
		input    *ai.Part
		wantType string
		wantData string
		wantErr  bool
	}{
		{
			input:    ai.NewMediaPart("text/plain", "gs://storage"),
			wantType: "text/plain",
			wantData: "gs://storage",
		},
		{
			input:   ai.NewMediaPart("", "gs://storage"),
			wantErr: true,
		},
		{
			input:    ai.NewMediaPart("", "data:text/plain,a"),
			wantType: "text/plain",
			wantData: "a",
		},
		{
			input:    ai.NewMediaPart("text/plain", "data:,b"),
			wantType: "text/plain",
			wantData: "b",
		},
		{
			input:    ai.NewMediaPart("text/plain", "data:image/jpeg,c"),
			wantType: "text/plain",
			wantData: "c",
		},
		{
			input:    ai.NewMediaPart("", "data:text/plain;base64,ZA=="),
			wantType: "text/plain",
			wantData: "d",
		},
		{
			input:   ai.NewMediaPart("", "data:text/plain;base64,bad"),
			wantErr: true,
		},
		{
			input:   ai.NewTextPart("e"),
			wantErr: true,
		},
	}

	for i, test := range tests {
		gotType, gotData, gotErr := Data(test.input)
		if gotErr != nil {
			if !test.wantErr {
				t.Errorf("case %d: unexpected error %v", i, gotErr)
			}
		} else if test.wantErr {
			t.Errorf("case %d: unexpected success", i)
		} else {
			if gotType != test.wantType {
				t.Errorf("case %d: got type %q, want %q", i, gotType, test.wantType)
			}
			if string(gotData) != test.wantData {
				t.Errorf("case %d: got data %q, want %q", i, gotData, test.wantData)
			}
		}
	}
}
