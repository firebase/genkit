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
)

// A Document is a piece of data that can be embedded, indexed, or retrieved.
// It includes metadata. It can contain multiple parts.
type Document struct {
	// The data that is part of this document.
	Content []*Part `json:"content,omitempty"`
	// The metadata for this document.
	Metadata map[string]any `json:"metadata,omitempty"`
}

// A Part is one part of a [Document]. This may be plain text or it
// may be a URL (possibly a "data:" URL with embedded data).
type Part struct {
	isText      bool
	contentType string
	text        string
}

func NewTextPart(text string) *Part {
	return &Part{isText: true, text: text}
}
func NewBlobPart(mimeType, contents string) *Part {
	return &Part{isText: false, contentType: mimeType, text: contents}
}

// IsText reports whether the [Part] contains plain text.
func (p *Part) IsPlainText() bool {
	return p.isText
}

// Text returns the text. This is either plain text or a URL.
func (p *Part) Text() string {
	return p.text
}

// ContentType returns the type of the content.
// This is only interesting if IsText is false.
func (p *Part) ContentType() string {
	if p.isText {
		return "text/plain"
	}
	return p.contentType
}

// MarshalJSON is called by the JSON marshaler to write out a Part.
func (p *Part) MarshalJSON() ([]byte, error) {
	// This is not handled by the schema generator because
	// Part is defined in TypeScript as a union.

	if p.isText {
		v := TextPart{
			Text: p.text,
		}
		return json.Marshal(v)
	} else {
		v := MediaPart{
			Media: &MediaPartMedia{
				ContentType: p.contentType,
				Url: p.text,
			},
		}
		return json.Marshal(v)
	}
}

// UnmarshalJSON is called by the JSON unmarshaler to read a Part.
func (p *Part) UnmarshalJSON(b []byte) error {
	// This is not handled by the schema generator because
	// Part is defined in TypeScript as a union.

	var s struct {
		Text  string `json:"text,omitempty"`
		Media *MediaPartMedia `json:"media,omitempty"`
	}

	if err := json.Unmarshal(b, &s); err != nil {
		return err
	}

	if s.Media != nil {
		p.isText = false
		p.text = s.Media.Url
		p.contentType = s.Media.ContentType
	} else {
		p.isText = true
		p.text = s.Text
		p.contentType = ""
	}
	return nil
}

// DocumentFromText returns a [Document] containing a single plain text part.
// This takes ownership of the metadata map.
func DocumentFromText(text string, metadata map[string]any) *Document {
	return &Document{
		Content: []*Part{
			&Part{
				isText: true,
				text:   text,
			},
		},
		Metadata: metadata,
	}
}
