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

package genkit

import (
	"context"
	"errors"

	"github.com/firebase/genkit/go/ai"
)

type Chat struct {
	// Genkit
	Genkit *Genkit
	// The model to query
	Model ai.Model
	// The chats threadname
	ThreadName string
	// The chats session
	Session *Session
	// Message sent to the model as system instructions
	SystemText string
	// Optional prompt
	Prompt  *ai.Prompt
	Request *ChatRequest
	Stream  ai.ModelStreamingCallback
}

type ChatRequest struct {
	Config   any           `json:"config,omitempty"`
	Context  []any         `json:"context,omitempty"`
	Messages []*ai.Message `json:"messages,omitempty"`

	// Defines the output format and schema
	Schema any             `json:"schema,omitempty"`
	Format ai.OutputFormat `json:"outputformat,omitempty"`

	// Tools lists the available tools that the model can ask the client to run.
	Tools []ai.Tool `json:"tools,omitempty"`
}

// ChatOption configures params for the chat
type ChatOption func(c *Chat) error

// NewChat creates a new chat instance with the provided AI model and options.
// If no session or thread name is provided, it adds a new session and default thread.
func NewChat(ctx context.Context, g *Genkit, opts ...ChatOption) (chat *Chat, err error) {
	chat = &Chat{
		Genkit:  g,
		Request: &ChatRequest{},
	}

	for _, with := range opts {
		err := with(chat)
		if err != nil {
			return nil, err
		}
	}

	if chat.Session == nil {
		s, err := NewSession(g)
		if err != nil {
			return nil, err
		}
		chat.Session = s
	}

	if chat.ThreadName == "" {
		chat.ThreadName = "default"
	}

	return chat, nil
}

// Send sends a message to the chat, generating a response from the AI model.
// It retrieves the chat history from the session store, adds the new message
// to the history, and sends the entire conversation to the AI model for
// generating a response. If a system message is set for the chat, it is
// included in the conversation before the history.
func (c *Chat) Send(ctx context.Context, msg string) (resp *ai.ModelResponse, err error) {
	// Load history
	data, err := c.Session.Store.Get(c.Session.ID)
	if err != nil {
		return nil, err
	}

	var messages []*ai.Message
	if c.SystemText != "" {
		// Add system message before history
		messages = append(messages, ai.NewSystemTextMessage(c.SystemText))
	}

	// Add new message after history
	messages = append(messages, data.Threads[c.ThreadName]...)
	messages = append(messages, ai.NewUserTextMessage(msg))

	// Assemble options
	var generateOptions []ai.GenerateOption
	generateOptions = append(generateOptions, ai.WithModel(c.Model))
	generateOptions = append(generateOptions, ai.WithMessages(messages...))
	generateOptions = append(generateOptions, ai.WithConfig(c.Request.Config))
	generateOptions = append(generateOptions, ai.WithStreaming(c.Stream))
	generateOptions = append(generateOptions, ai.WithTools(c.Request.Tools...))
	generateOptions = append(generateOptions, ai.WithContext(c.Request.Context...))

	if c.Request.Format != "" {
		generateOptions = append(generateOptions, ai.WithOutputFormat(c.Request.Format))
	}
	if c.Request.Schema != nil {
		generateOptions = append(generateOptions, ai.WithOutputSchema(c.Request.Schema))
	}

	// Call generate
	resp, err = ai.Generate(ctx,
		c.Genkit.reg,
		generateOptions...,
	)
	if err != nil {
		return nil, err
	}

	// Update history
	messages = append(messages, resp.Message)
	err = c.UpdateMessages(c.ThreadName, messages)
	if err != nil {
		return nil, err
	}

	return resp, nil
}

// UpdateMessages updates the messages for the chat.
func (c *Chat) UpdateMessages(ThreadName string, messages []*ai.Message) error {
	c.Request.Messages = messages
	return c.Session.UpdateMessages(ThreadName, messages)
}

// WithModel sets the model for the chat.
func WithModel(model ai.Model) ChatOption {
	return func(c *Chat) error {
		if c.Model != nil {
			return errors.New("cannot set model (WithModel) more than once")
		}
		c.Model = model
		return nil
	}
}

// WithSession sets a session for the chat.
func WithSession(session *Session) ChatOption {
	return func(c *Chat) error {
		if c.Session != nil {
			return errors.New("cannot set session (WithSession) more than once")
		}
		c.Session = session
		return nil
	}
}

// WithThreadName sets a thread name for the chat.
// This is used to seperate different conversions within the same session.
func WithThreadName(name string) ChatOption {
	return func(c *Chat) error {
		if c.ThreadName != "" {
			return errors.New("cannot set threadname (WithThreadName) more than once")
		}

		c.ThreadName = name
		return nil
	}
}

// WithStreaming adds a streaming callback to the chat request.
func WithStreaming(cb ai.ModelStreamingCallback) ChatOption {
	return func(c *Chat) error {
		if c.Stream != nil {
			return errors.New("cannot set streaming callback (WithStreaming) more than once")
		}
		c.Stream = cb
		return nil
	}
}

// WithSystemText sets a system message for the chat.
func WithSystemText(msg string) ChatOption {
	return func(c *Chat) error {
		if c.SystemText != "" {
			return errors.New("cannot set systemText (WithSystemText) more than once")
		}
		c.SystemText = msg
		return nil
	}
}

// WithConfig adds provided config to chat.
func WithConfig(config ai.GenerationCommonConfig) ChatOption {
	return func(c *Chat) error {
		if c.Request.Config != nil {
			return errors.New("cannot set config (WithConfig) more than once")
		}
		c.Request.Config = &config
		return nil
	}
}

// WithContext adds provided context to chat.
func WithContext(context ...any) ChatOption {
	return func(c *Chat) error {
		if len(c.Request.Context) > 0 {
			return errors.New("cannot set context (WithContext) more than once")
		}
		c.Request.Context = append(c.Request.Context, context...)
		return nil
	}
}

// WithTools adds provided tools to the chat.
func WithTools(tools ...ai.Tool) ChatOption {
	return func(c *Chat) error {
		if len(c.Request.Tools) != 0 {
			return errors.New("cannot set tools (WithTools) more than once")
		}
		c.Request.Tools = tools
		return nil
	}
}

// WithOutputSchema adds provided output schema to the chat.
func WithOutputSchema(schema any) ChatOption {
	return func(c *Chat) error {
		if c.Request.Schema != nil {
			return errors.New("cannot set outputSchema (WithOutputSchema) more than once")
		}

		c.Request.Schema = schema
		return nil
	}
}

// WithOutputFormat adds provided output format to the chat.
func WithOutputFormat(format ai.OutputFormat) ChatOption {
	return func(c *Chat) error {
		if c.Request.Format != "" {
			return errors.New("cannot set outputFormat (WithOutputFormat) more than once")
		}

		c.Request.Format = format
		return nil
	}
}
