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

func NewGenerateRequest() *GenerateRequest {
	return &GenerateRequest{}
}

func NewUserTextGenerateRequest(text string) *GenerateRequest {
	return NewGenerateRequest().AddUserTextMessage(text)
}

func (req *GenerateRequest) AddMessage(msg *Message) *GenerateRequest {
	req.Messages = append(req.Messages, msg)
	return req
}

func (req *GenerateRequest) SetConfig(config any) *GenerateRequest {
	req.Config = config
	return req
}

func (req *GenerateRequest) SetContext(context []any) *GenerateRequest {
	req.Context = context
	return req
}

func (req *GenerateRequest) SetTools(tools []*ToolDefinition) *GenerateRequest {
	req.Tools = tools
	return req
}

func (req *GenerateRequest) SetOutput(output *GenerateRequestOutput) *GenerateRequest {
	req.Output = output
	return req
}

func (req *GenerateRequest) AddUserTextMessage(text string) *GenerateRequest {
	req.AddMessage(NewMessage(RoleUser).AddPart(NewTextPart(text)))
	return req
}

func NewMessage(role Role) *Message {
	return &Message{
		Role: role,
	}
}

func NewTextMessage(role Role, text string) *Message {
	return &Message{
		Role:    role,
		Content: []*Part{NewTextPart(text)},
	}
}

func (msg *Message) AddPart(part *Part) *Message {
	msg.Content = append(msg.Content, part)
	return msg
}
