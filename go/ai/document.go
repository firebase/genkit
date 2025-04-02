// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"encoding/json"
	"fmt"

	"gopkg.in/yaml.v3"
)

type OutputFormat string

const (
	OutputFormatText  OutputFormat = "text"
	OutputFormatJSON  OutputFormat = "json"
	OutputFormatJSONL OutputFormat = "jsonl"
	OutputFormatMedia OutputFormat = "media"
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
	Kind         PartKind       `json:"kind,omitempty"`
	ContentType  string         `json:"contentType,omitempty"`  // valid for kind==blob
	Text         string         `json:"text,omitempty"`         // valid for kind∈{text,blob}
	ToolRequest  *ToolRequest   `json:"toolRequest,omitempty"`  // valid for kind==partToolRequest
	ToolResponse *ToolResponse  `json:"toolResponse,omitempty"` // valid for kind==partToolResponse
	Metadata     map[string]any `json:"metadata,omitempty"`     // valid for all kinds
}

type PartKind int8

const (
	PartText PartKind = iota
	PartMedia
	PartData
	PartToolRequest
	PartToolResponse
)

// NewTextPart returns a Part containing text.
func NewTextPart(text string) *Part {
	return &Part{Kind: PartText, ContentType: "plain/text", Text: text}
}

// NewJSONPart returns a Part containing JSON.
func NewJSONPart(text string) *Part {
	return &Part{Kind: PartText, ContentType: "application/json", Text: text}
}

// NewMediaPart returns a Part containing structured data described
// by the given mimeType.
func NewMediaPart(mimeType, contents string) *Part {
	return &Part{Kind: PartMedia, ContentType: mimeType, Text: contents}
}

// NewDataPart returns a Part containing raw string data.
func NewDataPart(contents string) *Part {
	return &Part{Kind: PartData, Text: contents}
}

// NewToolRequestPart returns a Part containing a request from
// the model to the client to run a Tool.
// (Only genkit plugins should need to use this function.)
func NewToolRequestPart(r *ToolRequest) *Part {
	return &Part{Kind: PartToolRequest, ToolRequest: r}
}

// NewToolResponsePart returns a Part containing the results
// of applying a Tool that the model requested.
func NewToolResponsePart(r *ToolResponse) *Part {
	return &Part{Kind: PartToolResponse, ToolResponse: r}
}

// IsText reports whether the [Part] contains plain text.
func (p *Part) IsText() bool {
	return p.Kind == PartText
}

// IsMedia reports whether the [Part] contains structured media data.
func (p *Part) IsMedia() bool {
	return p.Kind == PartMedia
}

// IsData reports whether the [Part] contains unstructured data.
func (p *Part) IsData() bool {
	return p.Kind == PartData
}

// IsToolRequest reports whether the [Part] contains a request to run a tool.
func (p *Part) IsToolRequest() bool {
	return p.Kind == PartToolRequest
}

// IsToolResponse reports whether the [Part] contains the result of running a tool.
func (p *Part) IsToolResponse() bool {
	return p.Kind == PartToolResponse
}

// MarshalJSON is called by the JSON marshaler to write out a Part.
func (p *Part) MarshalJSON() ([]byte, error) {
	// This is not handled by the schema generator because
	// Part is defined in TypeScript as a union.

	switch p.Kind {
	case PartText:
		v := textPart{
			Text:     p.Text,
			Metadata: p.Metadata,
		}
		return json.Marshal(v)
	case PartMedia:
		v := mediaPart{
			Media: &Media{
				ContentType: p.ContentType,
				Url:         p.Text,
			},
			Metadata: p.Metadata,
		}
		return json.Marshal(v)
	case PartData:
		v := dataPart{
			Data:     p.Text,
			Metadata: p.Metadata,
		}
		return json.Marshal(v)
	case PartToolRequest:
		v := toolRequestPart{
			ToolRequest: p.ToolRequest,
			Metadata:    p.Metadata,
		}
		return json.Marshal(v)
	case PartToolResponse:
		v := toolResponsePart{
			ToolResponse: p.ToolResponse,
			Metadata:     p.Metadata,
		}
		return json.Marshal(v)
	default:
		return nil, fmt.Errorf("invalid part kind %v", p.Kind)
	}
}

type partSchema struct {
	Text         string         `json:"text,omitempty" yaml:"text,omitempty"`
	Media        *Media         `json:"media,omitempty" yaml:"media,omitempty"`
	Data         string         `json:"data,omitempty" yaml:"data,omitempty"`
	ToolRequest  *ToolRequest   `json:"toolRequest,omitempty" yaml:"toolRequest,omitempty"`
	ToolResponse *ToolResponse  `json:"toolResponse,omitempty" yaml:"toolResponse,omitempty"`
	Metadata     map[string]any `json:"metadata,omitempty" yaml:"metadata,omitempty"`
}

// unmarshalPartFromSchema updates Part p based on the schema s.
func (p *Part) unmarshalPartFromSchema(s partSchema) {
	switch {
	case s.Media != nil:
		p.Kind = PartMedia
		p.Text = s.Media.Url
		p.ContentType = s.Media.ContentType
	case s.ToolRequest != nil:
		p.Kind = PartToolRequest
		p.ToolRequest = s.ToolRequest
	case s.ToolResponse != nil:
		p.Kind = PartToolResponse
		p.ToolResponse = s.ToolResponse
	default:
		p.Kind = PartText
		p.Text = s.Text
		p.ContentType = ""
		if s.Data != "" {
			// Note: if part is completely empty, we use text by default.
			p.Kind = PartData
			p.Text = s.Data
		}
	}
	p.Metadata = s.Metadata
}

// UnmarshalJSON is called by the JSON unmarshaler to read a Part.
func (p *Part) UnmarshalJSON(b []byte) error {
	var s partSchema
	if err := json.Unmarshal(b, &s); err != nil {
		return err
	}
	p.unmarshalPartFromSchema(s)
	return nil
}

// UnmarshalYAML implements yaml.Unmarshaler for Part.
func (p *Part) UnmarshalYAML(value *yaml.Node) error {
	var s partSchema
	if err := value.Decode(&s); err != nil {
		return err
	}
	p.unmarshalPartFromSchema(s)
	return nil
}

// JSONSchemaAlias tells the JSON schema reflection code to use a different
// type for the schema for this type. This is needed because the JSON
// marshaling of Part uses a schema that matches the TypeScript code,
// rather than the natural JSON marshaling. This matters because the
// current JSON validation code works by marshaling the JSON.
func (Part) JSONSchemaAlias() any {
	return partSchema{}
}

// DocumentFromText returns a [Document] containing a single plain text part.
// This takes ownership of the metadata map.
func DocumentFromText(text string, metadata map[string]any) *Document {
	return &Document{
		Content: []*Part{
			{
				Kind: PartText,
				Text: text,
			},
		},
		Metadata: metadata,
	}
}
