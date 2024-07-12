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
	Index         int              `json:"index"`
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

type dataPart struct {
	Data     any            `json:"data,omitempty"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

// A GenerateRequest is a request to generate completions from a model.
type GenerateRequest struct {
	// Candidates indicates the number of responses the model should generate.
	// Normally this would be set to 1.
	Candidates int   `json:"candidates,omitempty"`
	Config     any   `json:"config,omitempty"`
	Context    []any `json:"context,omitempty"`
	// Messages is a list of messages to pass to the model. The first n-1 Messages
	// are treated as history. The last Message is the current request.
	Messages []*Message `json:"messages,omitempty"`
	// Output describes the desired response format.
	Output *GenerateRequestOutput `json:"output,omitempty"`
	// Tools lists the available tools that the model can ask the client to run.
	Tools []*ToolDefinition `json:"tools,omitempty"`
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
	OutputFormatJSON  OutputFormat = "json"
	OutputFormatText  OutputFormat = "text"
	OutputFormatMedia OutputFormat = "media"
)

// A GenerateResponse is a model's response to a [GenerateRequest].
type GenerateResponse struct {
	// Candidates are the requested responses from the model. The length of this
	// slice will be equal to [GenerateRequest.Candidates].
	Candidates []*Candidate `json:"candidates,omitempty"`
	Custom     any          `json:"custom,omitempty"`
	// LatencyMs is the time the request took in milliseconds.
	LatencyMs float64 `json:"latencyMs,omitempty"`
	// Request is the [GenerateRequest] struct used to trigger this response.
	Request *GenerateRequest `json:"request,omitempty"`
	// Usage describes how many resources were used by this generation request.
	Usage *GenerationUsage `json:"usage,omitempty"`
}

// A GenerateResponseChunk is the portion of the [GenerateResponse]
// that is passed to a streaming callback.
type GenerateResponseChunk struct {
	Content []*Part `json:"content,omitempty"`
	Custom  any     `json:"custom,omitempty"`
	Index   int     `json:"index,omitempty"`
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
	Custom           map[string]float64 `json:"custom,omitempty"`
	InputCharacters  int                `json:"inputCharacters,omitempty"`
	InputImages      int                `json:"inputImages,omitempty"`
	InputTokens      int                `json:"inputTokens,omitempty"`
	OutputCharacters int                `json:"outputCharacters,omitempty"`
	OutputImages     int                `json:"outputImages,omitempty"`
	OutputTokens     int                `json:"outputTokens,omitempty"`
	TotalTokens      int                `json:"totalTokens,omitempty"`
}

type mediaPart struct {
	Data     any             `json:"data,omitempty"`
	Media    *mediaPartMedia `json:"media,omitempty"`
	Metadata map[string]any  `json:"metadata,omitempty"`
}

type mediaPartMedia struct {
	ContentType string `json:"contentType,omitempty"`
	Url         string `json:"url,omitempty"`
}

// Message is the contents of a model response.
type Message struct {
	Content  []*Part        `json:"content,omitempty"`
	Metadata map[string]any `json:"metadata,omitempty"`
	Role     Role           `json:"role,omitempty"`
}

type ModelInfo struct {
	Label    string             `json:"label,omitempty"`
	Supports *ModelInfoSupports `json:"supports,omitempty"`
	Versions []string           `json:"versions,omitempty"`
}

type ModelInfoSupports struct {
	Context    bool         `json:"context,omitempty"`
	Media      bool         `json:"media,omitempty"`
	Multiturn  bool         `json:"multiturn,omitempty"`
	Output     OutputFormat `json:"output,omitempty"`
	SystemRole bool         `json:"systemRole,omitempty"`
	Tools      bool         `json:"tools,omitempty"`
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
	Metadata map[string]any `json:"metadata,omitempty"`
	Text     string         `json:"text,omitempty"`
}

// A ToolDefinition describes a tool.
type ToolDefinition struct {
	Description string `json:"description,omitempty"`
	// Valid JSON Schema representing the input of the tool.
	InputSchema map[string]any `json:"inputSchema,omitempty"`
	Name        string         `json:"name,omitempty"`
	// Valid JSON Schema describing the output of the tool.
	OutputSchema map[string]any `json:"outputSchema,omitempty"`
}

// A ToolRequest is a message from the model to the client that it should run a
// specific tool and pass a [ToolResponse] to the model on the next chat request it makes.
// Any ToolRequest will correspond to some [ToolDefinition] previously sent by the client.
type ToolRequest struct {
	// Input is a JSON object describing the input values to the tool.
	// An example might be map[string]any{"country":"USA", "president":3}.
	Input map[string]any `json:"input,omitempty"`
	Name  string         `json:"name,omitempty"`
}

// A ToolResponse is a message from the client to the model containing
// the results of running a specific tool on the arguments passed to the client
// by the model in a [ToolRequest].
type ToolResponse struct {
	Name string `json:"name,omitempty"`
	// Output is a JSON object describing the results of running the tool.
	// An example might be map[string]any{"name":"Thomas Jefferson", "born":1743}.
	Output map[string]any `json:"output,omitempty"`
}
