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
	"fmt"
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
	Kind         partKind      `json:"kind,omitempty"`
	ContentType  string        `json:"contentType,omitempty"` // valid for kind==blob
	Text         string        `json:"text,omitempty"`        // valid for kind∈{text,blob}
	ToolRequest  *ToolRequest  `json:"toolreq,omitempty"`     // valid for kind==partToolRequest
	ToolResponse *ToolResponse `json:"toolresp,omitempty"`    // valid for kind==partToolResponse
}

type partKind int8

const (
	partText partKind = iota
	partMedia
	partData
	partToolRequest
	partToolResponse
)

// NewTextPart returns a Part containing text.
func NewTextPart(text string) *Part {
	return &Part{Kind: partText, ContentType: "plain/text", Text: text}
}

// NewMediaPart returns a Part containing structured data described
// by the given mimeType.
func NewMediaPart(mimeType, contents string) *Part {
	return &Part{Kind: partMedia, ContentType: mimeType, Text: contents}
}

// NewDataPart returns a Part containing raw string data.
func NewDataPart(contents string) *Part {
	return &Part{Kind: partData, Text: contents}
}

// NewToolRequestPart returns a Part containing a request from
// the model to the client to run a Tool.
// (Only genkit plugins should need to use this function.)
func NewToolRequestPart(r *ToolRequest) *Part {
	return &Part{Kind: partToolRequest, ToolRequest: r}
}

// NewToolResponsePart returns a Part containing the results
// of applying a Tool that the model requested.
func NewToolResponsePart(r *ToolResponse) *Part {
	return &Part{Kind: partToolResponse, ToolResponse: r}
}

// IsText reports whether the [Part] contains plain text.
func (p *Part) IsText() bool {
	return p.Kind == partText
}

// IsMedia reports whether the [Part] contains structured media data.
func (p *Part) IsMedia() bool {
	return p.Kind == partMedia
}

// IsData reports whether the [Part] contains unstructured data.
func (p *Part) IsData() bool {
	return p.Kind == partData
}

// IsToolRequest reports whether the [Part] contains a request to run a tool.
func (p *Part) IsToolRequest() bool {
	return p.Kind == partToolRequest
}

// IsToolResponse reports whether the [Part] contains the result of running a tool.
func (p *Part) IsToolResponse() bool {
	return p.Kind == partToolResponse
}

// MarshalJSON is called by the JSON marshaler to write out a Part.
func (p *Part) MarshalJSON() ([]byte, error) {
	// This is not handled by the schema generator because
	// Part is defined in TypeScript as a union.

	switch p.Kind {
	case partText:
		v := textPart{
			Text: p.Text,
		}
		return json.Marshal(v)
	case partMedia:
		v := mediaPart{
			Media: &mediaPartMedia{
				ContentType: p.ContentType,
				Url:         p.Text,
			},
		}
		return json.Marshal(v)
	case partData:
		v := dataPart{
			Data: p.Text,
		}
		return json.Marshal(v)
	case partToolRequest:
		// TODO: make sure these types marshal/unmarshal nicely
		// between Go and javascript. At the very least the
		// field name needs to change (here and in UnmarshalJSON).
		v := struct {
			ToolReq *ToolRequest `json:"toolreq,omitempty"`
		}{
			ToolReq: p.ToolRequest,
		}
		return json.Marshal(v)
	case partToolResponse:
		v := struct {
			ToolResp *ToolResponse `json:"toolresp,omitempty"`
		}{
			ToolResp: p.ToolResponse,
		}
		return json.Marshal(v)
	default:
		return nil, fmt.Errorf("invalid part kind %v", p.Kind)
	}
}

// UnmarshalJSON is called by the JSON unmarshaler to read a Part.
func (p *Part) UnmarshalJSON(b []byte) error {
	// This is not handled by the schema generator because
	// Part is defined in TypeScript as a union.

	var s struct {
		Text     string          `json:"text,omitempty"`
		Media    *mediaPartMedia `json:"media,omitempty"`
		Data     string          `json:"data,omitempty"`
		ToolReq  *ToolRequest    `json:"toolreq,omitempty"`
		ToolResp *ToolResponse   `json:"toolresp,omitempty"`
	}

	if err := json.Unmarshal(b, &s); err != nil {
		return err
	}

	switch {
	case s.Media != nil:
		p.Kind = partMedia
		p.Text = s.Media.Url
		p.ContentType = s.Media.ContentType
	case s.ToolReq != nil:
		p.Kind = partToolRequest
		p.ToolRequest = s.ToolReq
	case s.ToolResp != nil:
		p.Kind = partToolResponse
		p.ToolResponse = s.ToolResp
	default:
		p.Kind = partText
		p.Text = s.Text
		p.ContentType = ""
		if s.Data != "" {
			// Note: if part is completely empty, we use text by default.
			p.Kind = partData
			p.Text = s.Data
		}
	}
	return nil
}

// DocumentFromText returns a [Document] containing a single plain text part.
// This takes ownership of the metadata map.
func DocumentFromText(text string, metadata map[string]any) *Document {
	return &Document{
		Content: []*Part{
			{
				Kind: partText,
				Text: text,
			},
		},
		Metadata: metadata,
	}
}
