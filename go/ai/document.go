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
	kind         partKind
	contentType  string        // valid for kind==blob
	text         string        // valid for kind∈{text,blob}
	toolRequest  *ToolRequest  // valid for kind==partToolRequest
	toolResponse *ToolResponse // valid for kind==partToolResponse
}

type partKind int8

const (
	partText partKind = iota
	partBlob
	partToolRequest
	partToolResponse
)

// NewTextPart returns a Part containing raw string data.
func NewTextPart(text string) *Part {
	return &Part{kind: partText, text: text}
}

// NewBlobPart returns a Part containing structured data described
// by the given mimeType.
func NewBlobPart(mimeType, contents string) *Part {
	return &Part{kind: partBlob, contentType: mimeType, text: contents}
}

// NewToolRequestPart returns a Part containing a request from
// the model to the client to run a Tool.
// (Only genkit plugins should need to use this function.)
func NewToolRequestPart(r *ToolRequest) *Part {
	return &Part{kind: partToolRequest, toolRequest: r}
}

// NewToolResponsePart returns a Part containing the results
// of applying a Tool that the model requested.
func NewToolResponsePart(r *ToolResponse) *Part {
	return &Part{kind: partToolResponse, toolResponse: r}
}

// IsText reports whether the [Part] contains plain text.
func (p *Part) IsText() bool {
	return p.kind == partText
}

// IsBlob reports whether the [Part] contains blob (non-plain-text) data.
func (p *Part) IsBlob() bool {
	return p.kind == partBlob
}

// IsToolRequest reports whether the [Part] contains a request to run a tool.
func (p *Part) IsToolRequest() bool {
	return p.kind == partToolRequest
}

// IsToolResponse reports whether the [Part] contains the result of running a tool.
func (p *Part) IsToolResponse() bool {
	return p.kind == partToolResponse
}

// Text returns the text. This is either plain text or a URL.
func (p *Part) Text() string {
	return p.text
}

// ContentType returns the type of the content.
// This is only interesting if IsBlob() is true.
func (p *Part) ContentType() string {
	if p.kind == partText {
		return "text/plain"
	}
	return p.contentType
}

// ToolRequest returns a request from the model for the client to run a tool.
// Valid only if [IsToolRequest] is true.
func (p *Part) ToolRequest() *ToolRequest {
	return p.toolRequest
}

// ToolResponse returns the tool response the client is sending to the model.
// Valid only if [IsToolResponse] is true.
func (p *Part) ToolResponse() *ToolResponse {
	return p.toolResponse
}

// MarshalJSON is called by the JSON marshaler to write out a Part.
func (p *Part) MarshalJSON() ([]byte, error) {
	// This is not handled by the schema generator because
	// Part is defined in TypeScript as a union.

	switch p.kind {
	case partText:
		v := textPart{
			Text: p.text,
		}
		return json.Marshal(v)
	case partBlob:
		v := mediaPart{
			Media: &mediaPartMedia{
				ContentType: p.contentType,
				Url:         p.text,
			},
		}
		return json.Marshal(v)
	case partToolRequest:
		// TODO: make sure these types marshal/unmarshal nicely
		// between Go and javascript. At the very least the
		// field name needs to change (here and in UnmarshalJSON).
		v := struct {
			ToolReq *ToolRequest `json:"toolreq,omitempty"`
		}{
			ToolReq: p.toolRequest,
		}
		return json.Marshal(v)
	case partToolResponse:
		v := struct {
			ToolResp *ToolResponse `json:"toolresp,omitempty"`
		}{
			ToolResp: p.toolResponse,
		}
		return json.Marshal(v)
	default:
		return nil, fmt.Errorf("invalid part kind %v", p.kind)
	}
}

// UnmarshalJSON is called by the JSON unmarshaler to read a Part.
func (p *Part) UnmarshalJSON(b []byte) error {
	// This is not handled by the schema generator because
	// Part is defined in TypeScript as a union.

	var s struct {
		Text     string          `json:"text,omitempty"`
		Media    *mediaPartMedia `json:"media,omitempty"`
		ToolReq  *ToolRequest    `json:"toolreq,omitempty"`
		ToolResp *ToolResponse   `json:"toolresp,omitempty"`
	}

	if err := json.Unmarshal(b, &s); err != nil {
		return err
	}

	switch {
	case s.Media != nil:
		p.kind = partBlob
		p.text = s.Media.Url
		p.contentType = s.Media.ContentType
	case s.ToolReq != nil:
		p.kind = partToolRequest
		p.toolRequest = s.ToolReq
	case s.ToolResp != nil:
		p.kind = partToolResponse
		p.toolResponse = s.ToolResp
	default:
		p.kind = partText
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
				kind: partText,
				text: text,
			},
		},
		Metadata: metadata,
	}
}
