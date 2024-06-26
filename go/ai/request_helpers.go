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

// NewUserTextGenerateRequest creates a new GenerateRequest with a message with
// role set to "user" and context to single text part with the content of
// provided text.
func NewUserTextGenerateRequest(text string) *GenerateRequest {
	return &GenerateRequest{
		Messages: []*Message{
			{
				Role:    RoleUser,
				Content: []*Part{NewTextPart(text)},
			},
		},
	}
}

// NewGenerateRequest create a new GenerateRequest with provided config and
// messages.
func NewGenerateRequest(config map[string]any, messages ...*Message) *GenerateRequest {
	return &GenerateRequest{
		Config:   config,
		Messages: messages,
	}
}

// NewUserMessage creates a new Message with role "user" and provided parts.
func NewUserMessage(parts ...*Part) *Message {
	return NewMessage(RoleUser, nil, parts...)
}

// NewUserTextMessage creates a new Message with role "user" and content with
// a single text part with the content of provided text.
func NewUserTextMessage(text string) *Message {
	return NewTextMessage(RoleUser, text)
}

// NewModelMessage creates a new Message with role "model" and provided parts.
func NewModelMessage(parts ...*Part) *Message {
	return NewMessage(RoleModel, nil, parts...)
}

// NewUserTextMessage creates a new Message with role "model" and content with
// a single text part with the content of provided text.
func NewModelTextMessage(text string) *Message {
	return NewTextMessage(RoleModel, text)
}

// NewModelMessage creates a new Message with role "system" and provided parts.
func NewSystemMessage(parts ...*Part) *Message {
	return NewMessage(RoleSystem, nil, parts...)
}

// NewUserTextMessage creates a new Message with role "system" and content with
// a single text part with the content of provided text.
func NewSystemTextMessage(text string) *Message {
	return NewMessage(RoleSystem, nil, NewTextPart(text))
}

// NewMessage creates a new Message with the provided role, metadata and parts.
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
