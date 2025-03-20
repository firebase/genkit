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

package formatter

import (
	"encoding/json"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/invopop/jsonschema"
)

type jsonFormatter struct {
	formatName string
	output     ai.ModelRequestOutput
}

type jsonHandler struct {
	instructions string
	output       ai.ModelRequestOutput
}

func (j jsonFormatter) Name() string {
	return j.formatName
}

func (j jsonFormatter) Config() ai.ModelRequestOutput {
	return j.output
}

func (j jsonFormatter) Handler(schema *jsonschema.Schema) ai.FormatterHandler {
	var instructions string
	if schema != nil {
		instructions = "Output should be in JSON format and conform to the following schema"
	}
	handler := &jsonHandler{
		instructions: instructions,
	}

	return handler
}

func (j jsonHandler) ParseMessage(m *ai.Message) (*ai.Message, error) {
	text := base.ExtractJSONFromMarkdown(m.Text())
	var schemaBytes []byte
	schemaBytes, err := json.Marshal(j.output.Schema)
	if err != nil {
		return nil, fmt.Errorf("expected schema is not valid: %w", err)
	}
	if err = base.ValidateRaw([]byte(text), schemaBytes); err != nil {
		return nil, err
	}
	// TODO: Verify that it okay to replace all content with JSON.
	m.Content = []*ai.Part{ai.NewJSONPart(text)}

	return m, nil
}

func (j jsonHandler) Instructions() string {
	return j.instructions
}
