// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ai

// NewModelRequest create a new ModelRequest with provided config and
// messages.
func NewModelRequest(config any, messages ...*Message) *ModelRequest {
	return &ModelRequest{
		Config:   config,
		Messages: messages,
	}
}

// NewUserMessage creates a new Message with role "user" and provided parts.
// Use NewUserTextMessage if you have a text-only message.
func NewUserMessage(parts ...*Part) *Message {
	return NewMessage(RoleUser, nil, parts...)
}

// NewUserTextMessage creates a new Message with role "user" and content with
// a single text part with the content of provided text.
func NewUserTextMessage(text string) *Message {
	return NewTextMessage(RoleUser, text)
}

// NewModelMessage creates a new Message with role "model" and provided parts.
// Use NewModelTextMessage if you have a text-only message.
func NewModelMessage(parts ...*Part) *Message {
	return NewMessage(RoleModel, nil, parts...)
}

// NewUserTextMessage creates a new Message with role "model" and content with
// a single text part with the content of provided text.
func NewModelTextMessage(text string) *Message {
	return NewTextMessage(RoleModel, text)
}

// NewSystemMessage creates a new Message with role "system" and provided parts.
// Use NewSystemTextMessage if you have a text-only message.
func NewSystemMessage(parts ...*Part) *Message {
	return NewMessage(RoleSystem, nil, parts...)
}

// NewUserTextMessage creates a new Message with role "system" and content with
// a single text part with the content of provided text.
func NewSystemTextMessage(text string) *Message {
	return NewTextMessage(RoleSystem, text)
}

// NewMessage creates a new Message with the provided role, metadata and parts.
// Use NewTextMessage if you have a text-only message.
func NewMessage(role Role, metadata map[string]any, parts ...*Part) *Message {
	return &Message{
		Role:     role,
		Content:  parts,
		Metadata: metadata,
	}
}

// NewTextMessage creates a new Message with the provided role and content with
// a single part containint provided text.
func NewTextMessage(role Role, text string) *Message {
	return &Message{
		Role:    role,
		Content: []*Part{NewTextPart(text)},
	}
}
