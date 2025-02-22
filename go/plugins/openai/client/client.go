// Package client provides a custom OpenAI API client implementation
package client

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const (
	defaultBaseURL = "https://api.openai.com/v1"
	defaultTimeout = 30 * time.Second
)

// Client handles communication with OpenAI API
type Client struct {
	baseURL    string
	apiKey     string
	httpClient *http.Client
	orgID      string
}

// ClientBuilder provides a builder pattern for creating the custom client
type ClientBuilder struct {
	client *Client
	err    error
}

// NewClient starts a new client builder chain
func NewClient(apiKey string) *ClientBuilder {
	if apiKey == "" {
		return &ClientBuilder{err: fmt.Errorf("API key is required")}
	}

	return &ClientBuilder{
		client: &Client{
			baseURL: defaultBaseURL,
			apiKey:  apiKey,
			httpClient: &http.Client{
				Timeout: defaultTimeout,
			},
		},
	}
}

// WithBaseURL sets a custom base URL
func (b *ClientBuilder) WithBaseURL(url string) *ClientBuilder {
	if b.err != nil {
		return b
	}
	if url == "" {
		b.err = fmt.Errorf("base URL cannot be empty")
		return b
	}
	b.client.baseURL = url
	return b
}

// WithTimeout sets a custom timeout for the HTTP client
func (b *ClientBuilder) WithTimeout(timeout time.Duration) *ClientBuilder {
	if b.err != nil {
		return b
	}
	if timeout <= 0 {
		b.err = fmt.Errorf("timeout must be positive")
		return b
	}
	b.client.httpClient.Timeout = timeout
	return b
}

// WithHTTPClient sets a custom HTTP client
func (b *ClientBuilder) WithHTTPClient(httpClient *http.Client) *ClientBuilder {
	if b.err != nil {
		return b
	}
	if httpClient == nil {
		b.err = fmt.Errorf("HTTP client cannot be nil")
		return b
	}
	b.client.httpClient = httpClient
	return b
}

// WithOrganization sets an organization ID
func (b *ClientBuilder) WithOrganization(orgID string) *ClientBuilder {
	if b.err != nil {
		return b
	}
	b.client.orgID = orgID
	return b
}

// Build creates the client or returns any error that occurred during building
func (b *ClientBuilder) Build() (*Client, error) {
	if b.err != nil {
		return nil, b.err
	}
	return b.client, nil
}

// ChatCompletionBuilder provides a builder for chat completion requests
// this models OpenAI's chat completions API
// https://platform.openai.com/docs/guides/text-generation#chat-completions
//
// example:
//
//	builder := client.NewChatCompletion("gpt-4").
//		AddMessage("user", "Hello, how are you?").
//		WithTemperature(0.5).
//		WithMaxTokens(100).
type ChatCompletionBuilder struct {
	request *ChatCompletionRequest
	client  *Client
	err     error
}

// NewChatCompletion starts a new chat completion request builder
func (c *Client) NewChatCompletion(model string) *ChatCompletionBuilder {
	if model == "" {
		return &ChatCompletionBuilder{err: fmt.Errorf("model is required")}
	}

	return &ChatCompletionBuilder{
		client: c,
		request: &ChatCompletionRequest{
			Model:    model,
			Messages: make([]ChatMessage, 0),
		},
	}
}

// AddMessage adds a message to the chat completion request
// the role must be one of the defined roles in the Role type
// as defined in the OpenAI API
// https://platform.openai.com/docs/guides/text-generation#messages-and-roles
//
// example:
//
//	builder.AddMessage("user", "Hello, how are you?")
func (b *ChatCompletionBuilder) AddMessage(role Role, content string) *ChatCompletionBuilder {
	if b.err != nil {
		return b
	}
	if role == "" || content == "" {
		b.err = fmt.Errorf("role and content are required")
		return b
	}
	b.request.Messages = append(b.request.Messages, ChatMessage{
		Role:    role,
		Content: content,
	})
	return b
}

// WithTemperature sets the temperature for the request
func (b *ChatCompletionBuilder) WithTemperature(temp float64) *ChatCompletionBuilder {
	if b.err != nil {
		return b
	}
	if temp < 0 || temp > 2 {
		b.err = fmt.Errorf("temperature must be between 0 and 2")
		return b
	}
	b.request.Temperature = temp
	return b
}

// WithMaxTokens sets the max tokens for the request
func (b *ChatCompletionBuilder) WithMaxTokens(tokens int) *ChatCompletionBuilder {
	if b.err != nil {
		return b
	}
	if tokens <= 0 {
		b.err = fmt.Errorf("max tokens must be positive")
		return b
	}
	b.request.MaxTokens = tokens
	return b
}

// Execute sends the chat completion request
func (b *ChatCompletionBuilder) Execute(ctx context.Context) (*ChatCompletionResponse, error) {
	if b.err != nil {
		return nil, b.err
	}
	if len(b.request.Messages) == 0 {
		return nil, fmt.Errorf("at least one message is required")
	}

	resp, err := b.client.sendRequest(ctx, "/chat/completions", b.request)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result ChatCompletionResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// ExecuteStream sends a streaming chat completion request
func (b *ChatCompletionBuilder) ExecuteStream(ctx context.Context) (*ChatCompletionStream, error) {
	if b.err != nil {
		return nil, b.err
	}
	if len(b.request.Messages) == 0 {
		return nil, fmt.Errorf("at least one message is required")
	}

	b.request.Stream = true
	resp, err := b.client.sendRequest(ctx, "/chat/completions", b.request)
	if err != nil {
		return nil, err
	}

	return newChatCompletionStream(resp), nil
}

// sendRequest handles the HTTP communication
func (c *Client) sendRequest(ctx context.Context, endpoint string, body interface{}) (*http.Response, error) {
	jsonBody, err := json.Marshal(body)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(
		ctx,
		"POST",
		c.baseURL+endpoint,
		bytes.NewReader(jsonBody),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	if c.orgID != "" {
		req.Header.Set("OpenAI-Organization", c.orgID)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, fmt.Errorf("OpenAI API error: %s: %s", resp.Status, string(body))
	}

	return resp, nil
}
