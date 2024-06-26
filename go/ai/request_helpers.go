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

func NewGenerateRequest(config map[string]any, messages ...*Message) *GenerateRequest {
	return &GenerateRequest{
		Config:   config,
		Messages: messages,
	}
}

func NewUserMessage(parts ...*Part) *Message {
	return NewMessage(RoleUser, nil, parts...)
}
func NewUserTextMessage(text string) *Message {
	return NewMessage(RoleUser, nil, NewTextPart(text))
}

func NewModelMessage(parts ...*Part) *Message {
	return NewMessage(RoleModel, nil, parts...)
}

func NewModelTextMessage(text string) *Message {
	return NewMessage(RoleModel, nil, NewTextPart(text))
}

func NewSystemMessage(parts ...*Part) *Message {
	return NewMessage(RoleSystem, nil, parts...)
}

func NewSystemTextMessage(text string) *Message {
	return NewMessage(RoleSystem, nil, NewTextPart(text))
}

func NewMessage(role Role, metadata map[string]any, parts ...*Part) *Message {
	return &Message{
		Role:     role,
		Content:  parts,
		Metadata: metadata,
	}
}

func NewTextMessage(role Role, text string) *Message {
	return &Message{
		Role:    role,
		Content: []*Part{NewTextPart(text)},
	}
}
