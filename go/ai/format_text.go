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

type TextFormatter struct {
	FormatName string
}

type textHandler struct {
	instructions string
	output       *ModelOutputConfig
}

func (t TextFormatter) Name() string {
	return t.FormatName
}

func (t textHandler) Config() *ModelOutputConfig {
	return t.output
}

func (t textHandler) Instructions() string {
	return t.instructions
}

func (t TextFormatter) Handler(schema map[string]any) FormatterHandler {
	handler := &textHandler{
		output: &ModelOutputConfig{
			ContentType: "text/plain",
		},
	}

	return handler
}

func (t textHandler) ParseMessage(m *Message) (*Message, error) {
	return m, nil
}
