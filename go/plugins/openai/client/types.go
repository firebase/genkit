package client

import (
	"io"
	"net/http"
)

// ChatCompletionRequest represents a request to the chat completions API
type ChatCompletionRequest struct {
	Model       string        `json:"model"`
	Messages    []ChatMessage `json:"messages"`
	Temperature float64       `json:"temperature,omitempty"`
	MaxTokens   int           `json:"max_tokens,omitempty"`
	Stream      bool          `json:"stream,omitempty"`
	Stop        []string      `json:"stop,omitempty"`
	TopP        float64       `json:"top_p,omitempty"`
}

// Role defines the possible roles in a chat conversation
// These roles are explictly defined in OpenAI's API
// https://platform.openai.com/docs/guides/text-generation#messages-and-roles
type Role string

const (
	RoleSystem    Role = "system"
	RoleUser      Role = "user"
	RoleAssistant Role = "assistant"
)

// ChatMessage represents a message in the conversation
type ChatMessage struct {
	Role    Role   `json:"role"`
	Content string `json:"content"`
}

// ChatCompletionResponse represents a response from the chat completions API
type ChatCompletionResponse struct {
	ID      string       `json:"id"`
	Choices []ChatChoice `json:"choices"`
	Usage   Usage        `json:"usage"`
}

type ChatChoice struct {
	Index        int         `json:"index"`
	Message      ChatMessage `json:"message"`
	FinishReason string      `json:"finish_reason"`
}

type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// Streaming types
type ChatCompletionStream struct {
	reader io.ReadCloser
	resp   *http.Response
}

type StreamChunk struct {
	Choices []StreamChoice `json:"choices"`
}

type StreamChoice struct {
	Delta struct {
		Content string `json:"content"`
	} `json:"delta"`
}
