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
	// The model to query
	Model ai.Model

	// The chats threadname
	ThreadName string

	// The chats session
	Session *Session

	// Message sent to the model as system instructions
	SystemText string
	//Config     *ai.GenerationCommonConfig

	Request *ai.ModelRequest
	Stream  ai.ModelStreamingCallback
}

// ChatOption configures params for the chat
type ChatOption func(c *Chat) error

// NewChat creates a new chat instance with the provided AI model and options.
// If no session or thread name is provided, it adds a new session and default thread.
func NewChat(ctx context.Context, m ai.Model, opts ...ChatOption) (chat *Chat, err error) {
	chat = &Chat{
		Model:   m,
		Request: &ai.ModelRequest{},
	}

	for _, with := range opts {
		err := with(chat)
		if err != nil {
			return nil, err
		}
	}

	if chat.Session == nil {
		s, err := NewSession()
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
	// load history
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
	// TODO Error handling if thread doesn't exist in history
	history := data.Threads[c.ThreadName]
	messages = append(messages, history...)
	messages = append(messages, ai.NewUserTextMessage(msg))

	resp, err = ai.Generate(ctx,
		c.Model,
		ai.WithMessages(messages...),
		ai.WithConfig(c.Request.Config),
		ai.WithStreaming(c.Stream),
	)
	if err != nil {
		return nil, err
	}

	// update history
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
func WithContext(c ...any) ChatOption {
	return func(c *Chat) error {
		c.Request.Context = append(c.Request.Context, c.Request.Context...)
		return nil
	}
}

// WithTextPrompt adds a simple text user prompt to ModelRequest.
// func WithTextPrompt(prompt string) GenerateOption {
// 	return func(req *generateParams) error {
// 		req.Request.Messages = append(req.Request.Messages, NewUserTextMessage(prompt))
// 		return nil
// 	}
// }

// WithTools adds provided tools to ModelRequest.
// func WithTools(tools ...Tool) GenerateOption {
// 	return func(req *generateParams) error {
// 		var toolDefs []*ToolDefinition
// 		for _, t := range tools {
// 			toolDefs = append(toolDefs, t.Definition())
// 		}
// 		req.Request.Tools = toolDefs
// 		return nil
// 	}
// }

// WithOutputSchema adds provided output schema to ModelRequest.
// func WithOutputSchema(schema any) GenerateOption {
// 	return func(req *generateParams) error {
// 		if req.Request.Output != nil && req.Request.Output.Schema != nil {
// 			return errors.New("cannot set Request.Output.Schema (WithOutputSchema) more than once")
// 		}
// 		if req.Request.Output == nil {
// 			req.Request.Output = &ModelRequestOutput{}
// 			req.Request.Output.Format = OutputFormatJSON
// 		}
// 		req.Request.Output.Schema = base.SchemaAsMap(base.InferJSONSchemaNonReferencing(schema))
// 		return nil
// 	}
// }

// WithOutputFormat adds provided output format to ModelRequest.
// func WithOutputFormat(format OutputFormat) GenerateOption {
// 	return func(req *generateParams) error {
// 		if req.Request.Output == nil {
// 			req.Request.Output = &ModelRequestOutput{}
// 		}
// 		req.Request.Output.Format = format
// 		return nil
// 	}
// }
