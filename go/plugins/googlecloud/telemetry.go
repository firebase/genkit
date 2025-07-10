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

package googlecloud

import (
	"go.opentelemetry.io/otel/attribute"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// Telemetry interface that all telemetry modules implement
// This matches the tick pattern from the JavaScript implementation
type Telemetry interface {
	Tick(span sdktrace.ReadOnlySpan, logInputOutput bool, projectID string)
}

// SharedDimensions contains common metric dimensions used across telemetry modules
type SharedDimensions struct {
	FeatureName   string
	Path          string
	Status        string
	Source        string
	SourceVersion string
}

// GenerateRequestData represents the structure of input to a generate action
// This matches the JavaScript GenerateRequestData interface
type GenerateRequestData struct {
	Messages []Message `json:"messages"`
	Config   *Config   `json:"config,omitempty"`
}

// GenerateResponseData represents the structure of output from a generate action
// This matches the JavaScript GenerateResponseData interface
type GenerateResponseData struct {
	Message       *Message         `json:"message,omitempty"`
	Candidates    []*Candidate     `json:"candidates,omitempty"`
	Usage         *GenerationUsage `json:"usage,omitempty"`
	LatencyMs     float64          `json:"latencyMs,omitempty"`
	FinishReason  string           `json:"finishReason,omitempty"`
	FinishMessage string           `json:"finishMessage,omitempty"`
}

// Message represents a message in the conversation
type Message struct {
	Role    string `json:"role"`
	Content []Part `json:"content"`
}

// Part represents different types of content parts
type Part struct {
	Text         string            `json:"text,omitempty"`
	Data         interface{}       `json:"data,omitempty"`
	Media        *MediaPart        `json:"media,omitempty"`
	ToolRequest  *ToolRequestPart  `json:"toolRequest,omitempty"`
	ToolResponse *ToolResponsePart `json:"toolResponse,omitempty"`
	Custom       interface{}       `json:"custom,omitempty"`
}

// MediaPart represents media content
type MediaPart struct {
	URL         string `json:"url"`
	ContentType string `json:"contentType,omitempty"`
}

// ToolRequestPart represents a tool request
type ToolRequestPart struct {
	Name  string      `json:"name"`
	Ref   string      `json:"ref,omitempty"`
	Input interface{} `json:"input"`
}

// ToolResponsePart represents a tool response
type ToolResponsePart struct {
	Name   string      `json:"name"`
	Ref    string      `json:"ref,omitempty"`
	Output interface{} `json:"output"`
}

// Config represents generation configuration
type Config struct {
	MaxOutputTokens int      `json:"maxOutputTokens,omitempty"`
	StopSequences   []string `json:"stopSequences,omitempty"`
	Temperature     float64  `json:"temperature,omitempty"`
	TopK            int      `json:"topK,omitempty"`
	TopP            float64  `json:"topP,omitempty"`
}

// Candidate represents a generation candidate
type Candidate struct {
	Message *Message `json:"message"`
	Index   int      `json:"index"`
}

// GenerationUsage represents token/character usage statistics
type GenerationUsage struct {
	InputTokens      int64 `json:"inputTokens,omitempty"`
	OutputTokens     int64 `json:"outputTokens,omitempty"`
	InputCharacters  int64 `json:"inputCharacters,omitempty"`
	OutputCharacters int64 `json:"outputCharacters,omitempty"`
	InputImages      int64 `json:"inputImages,omitempty"`
	OutputImages     int64 `json:"outputImages,omitempty"`
}

// extractStringAttribute safely extracts a string attribute from span attributes
func extractStringAttribute(attrs []attribute.KeyValue, key string) string {
	for _, attr := range attrs {
		if string(attr.Key) == key {
			return attr.Value.AsString()
		}
	}
	return ""
}

// extractBoolAttribute safely extracts a boolean attribute from span attributes
func extractBoolAttribute(attrs []attribute.KeyValue, key string) bool {
	for _, attr := range attrs {
		if string(attr.Key) == key {
			return attr.Value.AsBool()
		}
	}
	return false
}

// extractInt64Attribute safely extracts an int64 attribute from span attributes
func extractInt64Attribute(attrs []attribute.KeyValue, key string) int64 {
	for _, attr := range attrs {
		if string(attr.Key) == key {
			return attr.Value.AsInt64()
		}
	}
	return 0
}

// truncate limits string length to maxLen characters, matching JS implementation
func truncate(text string, limit ...int) string {
	maxLen := MaxLogContentLength // Match JS: 128,000 characters
	if len(limit) > 0 && limit[0] > 0 {
		maxLen = limit[0]
	}

	if text == "" || len(text) <= maxLen {
		return text
	}

	return text[:maxLen]
}
