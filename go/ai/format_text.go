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
	output     OutputConfig
}

type textHandler struct {
	instructions string
	output       *OutputConfig
}

func (j TextFormatter) Name() string {
	return j.FormatName
}

func (j TextFormatter) Config() OutputConfig {
	return j.output
}

func (j TextFormatter) Handler(schema map[string]any) FormatterHandler {
	var instructions string
	if schema != nil {
		instructions = "Output should be in JSON format and conform to the following schema"
	}
	handler := &textHandler{
		instructions: instructions,
		output: &OutputConfig{
			ContentType: "text/plain",
		},
	}

	return handler
}

func (j textHandler) ParseMessage(m *Message) (*Message, error) {
	return m, nil
}

func (j textHandler) Instructions() string {
	return j.instructions
}
