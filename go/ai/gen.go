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

// This file was generated by jsonschemagen. DO NOT EDIT.

package ai

// A Candidate is one of several possible generated responses from a generation
// request. It contains a single generated message along with additional
// metadata about its generation. A generation request may result in multiple Candidates.
type Candidate struct {
	Custom        any              `json:"custom,omitempty"`
	FinishMessage string           `json:"finishMessage,omitempty"`
	FinishReason  FinishReason     `json:"finishReason,omitempty"`
	Index         int              `json:"index,omitempty"`
	Message       *Message         `json:"message,omitempty"`
	Usage         *GenerationUsage `json:"usage,omitempty"`
}

// FinishReason is the reason why a model stopped generating tokens.
type FinishReason string

const (
	FinishReasonStop    FinishReason = "stop"
	FinishReasonLength  FinishReason = "length"
	FinishReasonBlocked FinishReason = "blocked"
	FinishReasonOther   FinishReason = "other"
	FinishReasonUnknown FinishReason = "unknown"
)

// A GenerateRequest is a request to generate completions from a model.
type GenerateRequest struct {
	Candidates int `json:"candidates,omitempty"`
	Config     any `json:"config,omitempty"`
	// Messages is a list of messages to pass to the model. The first n-1 Messages
	// are treated as history. The last Message is the current request.
	Messages []*Message             `json:"messages,omitempty"`
	Output   *GenerateRequestOutput `json:"output,omitempty"`
	Tools    []*ToolDefinition      `json:"tools,omitempty"`
}

// GenerateRequestOutput describes the structure that the model's output
// should conform to. If Format is [OutputFormatJSON], then Schema
// can describe the desired form of the generated JSON.
type GenerateRequestOutput struct {
	Format OutputFormat   `json:"format,omitempty"`
	Schema map[string]any `json:"schema,omitempty"`
}

// OutputFormat is the format that the model's output should produce.
type OutputFormat string

const (
	OutputFormatJSON OutputFormat = "json"
	OutputFormatText OutputFormat = "text"
)

// A GenerateResponse is a model's response to a [GenerateRequest].
type GenerateResponse struct {
	Candidates []*Candidate     `json:"candidates,omitempty"`
	Custom     any              `json:"custom,omitempty"`
	Request    *GenerateRequest `json:"request,omitempty"`
	Usage      *GenerationUsage `json:"usage,omitempty"`
}

// GenerationCommonConfig holds configuration for generation.
type GenerationCommonConfig struct {
	MaxOutputTokens int      `json:"maxOutputTokens,omitempty"`
	StopSequences   []string `json:"stopSequences,omitempty"`
	Temperature     float64  `json:"temperature,omitempty"`
	TopK            int      `json:"topK,omitempty"`
	TopP            float64  `json:"topP,omitempty"`
	Version         string   `json:"version,omitempty"`
}

// GenerationUsage provides information about the generation process.
type GenerationUsage struct {
	Custom       map[string]float64 `json:"custom,omitempty"`
	InputTokens  float64            `json:"inputTokens,omitempty"`
	OutputTokens float64            `json:"outputTokens,omitempty"`
	TotalTokens  float64            `json:"totalTokens,omitempty"`
}

type mediaPart struct {
	Media *mediaPartMedia `json:"media,omitempty"`
}

type mediaPartMedia struct {
	ContentType string `json:"contentType,omitempty"`
	Url         string `json:"url,omitempty"`
}

// Message is the contents of a model response.
type Message struct {
	Content []*Part `json:"content,omitempty"`
	Role    Role    `json:"role,omitempty"`
}

// Role indicates which entity is responsible for the content of a message.
type Role string

const (
	// RoleSystem indicates this message is user-independent context.
	RoleSystem Role = "system"
	// RoleUser indicates this message was generated by the client.
	RoleUser Role = "user"
	// RoleModel indicates this message was generated by the model during a previous interaction.
	RoleModel Role = "model"
	// RoleTool indicates this message was generated by a local tool, likely triggered by a request
	// from the model in one of its previous responses.
	RoleTool Role = "tool"
)

type textPart struct {
	Text string `json:"text,omitempty"`
}

// A ToolDefinition describes a tool.
type ToolDefinition struct {
	// Valid JSON Schema representing the input of the tool.
	InputSchema map[string]any `json:"inputSchema,omitempty"`
	Name        string         `json:"name,omitempty"`
	// Valid JSON Schema describing the output of the tool.
	OutputSchema map[string]any `json:"outputSchema,omitempty"`
}

type ToolRequestPart struct {
	ToolRequest *ToolRequestPartToolRequest `json:"toolRequest,omitempty"`
}

type ToolRequestPartToolRequest struct {
	Input any    `json:"input,omitempty"`
	Name  string `json:"name,omitempty"`
	Ref   string `json:"ref,omitempty"`
}

type ToolResponsePart struct {
	ToolResponse *ToolResponsePartToolResponse `json:"toolResponse,omitempty"`
}

type ToolResponsePartToolResponse struct {
	Name   string `json:"name,omitempty"`
	Output any    `json:"output,omitempty"`
	Ref    string `json:"ref,omitempty"`
}
