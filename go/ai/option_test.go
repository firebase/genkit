// Copyright 2025 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"testing"

	"github.com/google/go-cmp/cmp"
	"github.com/google/go-cmp/cmp/cmpopts"
)

func TestCommonOptions(t *testing.T) {
	tests := []struct {
		name    string
		opts    []CommonGenOption
		wantErr bool
	}{
		{
			name: "valid options",
			opts: []CommonGenOption{
				WithMessages(NewUserTextMessage("test")),
				WithConfig(&GenerationCommonConfig{Temperature: 0.7}),
				WithModel(&mockModel{name: "test/model"}),
				WithTools(&mockTool{name: "test/tool"}),
				WithToolChoice(ToolChoiceAuto),
				WithMaxTurns(3),
				WithReturnToolRequests(true),
				WithMiddleware(func(next ModelFunc) ModelFunc { return next }),
			},
			wantErr: false,
		},
		{
			name: "mutually exclusive - messages",
			opts: []CommonGenOption{
				WithMessages(NewUserTextMessage("test")),
				WithMessagesFn(func(context.Context, any) ([]*Message, error) { return nil, nil }),
			},
			wantErr: true,
		},
		{
			name: "mutually exclusive - model",
			opts: []CommonGenOption{
				WithModel(&mockModel{name: "test/model"}),
				WithModelName("test/model"),
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			genOpts := &generateOptions{}
			promptOpts := &promptOptions{}
			pgOpts := &promptExecutionOptions{}

			var err error
			for _, opt := range tt.opts {
				err = opt.applyGenerate(genOpts)
				if err != nil {
					break
				}
			}

			if (err != nil) != tt.wantErr {
				t.Errorf("applyGenerate() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if tt.wantErr {
				return
			}

			for _, opt := range tt.opts {
				if err = opt.applyPrompt(promptOpts); err != nil {
					t.Errorf("applyPrompt() unexpected error = %v", err)
					return
				}
			}

			for _, opt := range tt.opts {
				if err = opt.applyPromptExecute(pgOpts); err != nil {
					t.Errorf("applyPromptExecute() unexpected error = %v", err)
					return
				}
			}
		})
	}
}

func TestPromptOptions(t *testing.T) {
	tests := []struct {
		name    string
		opts    []PromptOption
		wantErr bool
	}{
		{
			name: "valid options",
			opts: []PromptOption{
				WithDescription("test description"),
				WithMetadata(map[string]any{"key": "value"}),
				WithInputType(struct {
					Test string `json:"test"`
				}{}),
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			opts := &promptOptions{}
			var err error
			for _, opt := range tt.opts {
				err = opt.applyPrompt(opts)
				if err != nil {
					break
				}
			}
			if (err != nil) != tt.wantErr {
				t.Errorf("applyPrompt() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestPromptingOptions(t *testing.T) {
	tests := []struct {
		name    string
		opts    []PromptingOption
		wantErr bool
	}{
		{
			name: "valid options",
			opts: []PromptingOption{
				WithSystem("system instruction"),
				WithPrompt("user prompt"),
			},
			wantErr: false,
		},
		{
			name: "mutually exclusive - system",
			opts: []PromptingOption{
				WithSystem("system instruction"),
				WithSystemFn(func(context.Context, any) (string, error) { return "system", nil }),
			},
			wantErr: true,
		},
		{
			name: "mutually exclusive - prompt",
			opts: []PromptingOption{
				WithPrompt("user prompt"),
				WithPromptFn(func(context.Context, any) (string, error) { return "prompt", nil }),
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			genOpts := &generateOptions{}
			promptOpts := &promptOptions{}

			var err error
			for _, opt := range tt.opts {
				err = opt.applyGenerate(genOpts)
				if err != nil {
					break
				}
			}

			if (err != nil) != tt.wantErr {
				t.Errorf("applyGenerate() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if tt.wantErr {
				return
			}

			for _, opt := range tt.opts {
				if err = opt.applyPrompt(promptOpts); err != nil {
					t.Errorf("applyPrompt() unexpected error = %v", err)
					return
				}
			}
		})
	}
}

func TestOutputOptions(t *testing.T) {
	tests := []struct {
		name    string
		opts    []OutputOption
		wantErr bool
	}{
		{
			name: "valid - output type",
			opts: []OutputOption{
				WithOutputType(struct {
					Test string `json:"test"`
				}{}),
			},
			wantErr: false,
		},
		{
			name: "valid - output format",
			opts: []OutputOption{
				WithOutputFormat(OutputFormatText),
			},
			wantErr: false,
		},
		{
			name: "valid - output instruction",
			opts: []OutputOption{
				WithOutputInstructions(""),
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			genOpts := &generateOptions{}
			promptOpts := &promptOptions{}

			var err error
			for _, opt := range tt.opts {
				err = opt.applyGenerate(genOpts)
				if err != nil {
					break
				}
			}

			if (err != nil) != tt.wantErr {
				t.Errorf("applyGenerate() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if tt.wantErr {
				return
			}

			for _, opt := range tt.opts {
				if err = opt.applyPrompt(promptOpts); err != nil {
					t.Errorf("applyPrompt() unexpected error = %v", err)
					return
				}
			}
		})
	}
}

func TestExecutionOptions(t *testing.T) {
	tests := []struct {
		name    string
		opts    []ExecutionOption
		wantErr bool
	}{
		{
			name: "valid options",
			opts: []ExecutionOption{
				WithStreaming(func(context.Context, *ModelResponseChunk) error { return nil }),
			},
			wantErr: false,
		},
		{
			name: "duplicate - streaming",
			opts: []ExecutionOption{
				WithStreaming(func(context.Context, *ModelResponseChunk) error { return nil }),
				WithStreaming(func(context.Context, *ModelResponseChunk) error { return nil }),
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			genOpts := &generateOptions{}
			pgOpts := &promptExecutionOptions{}

			var err error
			for _, opt := range tt.opts {
				err = opt.applyGenerate(genOpts)
				if err != nil {
					break
				}
			}

			if (err != nil) != tt.wantErr {
				t.Errorf("applyGenerate() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if tt.wantErr {
				return
			}

			for _, opt := range tt.opts {
				if err = opt.applyPromptExecute(pgOpts); err != nil {
					t.Errorf("applyPromptExecute() unexpected error = %v", err)
					return
				}
			}
		})
	}
}

func TestPromptGenerateOptions(t *testing.T) {
	tests := []struct {
		name    string
		opts    []PromptExecuteOption
		wantErr bool
	}{
		{
			name: "valid options",
			opts: []PromptExecuteOption{
				WithInput(map[string]string{"key": "value"}),
			},
			wantErr: false,
		},
		{
			name: "duplicate - input",
			opts: []PromptExecuteOption{
				WithInput("input1"),
				WithInput("input2"),
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			opts := &promptExecutionOptions{}
			var err error
			for _, opt := range tt.opts {
				err = opt.applyPromptExecute(opts)
				if err != nil {
					break
				}
			}
			if (err != nil) != tt.wantErr {
				t.Errorf("applyPromptExecute() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestGenerateOptionsComplete(t *testing.T) {
	opts := &generateOptions{}

	mw := func(next ModelFunc) ModelFunc { return next }
	model := &mockModel{name: "test/model"}
	tool := &mockTool{name: "test/tool"}
	streamFunc := func(context.Context, *ModelResponseChunk) error { return nil }
	doc := DocumentFromText("doc", nil)
	options := []GenerateOption{
		WithModel(model),
		WithMessages(NewUserTextMessage("message")),
		WithConfig(&GenerationCommonConfig{Temperature: 0.7}),
		WithTools(tool),
		WithToolChoice(ToolChoiceAuto),
		WithMaxTurns(3),
		WithReturnToolRequests(true),
		WithMiddleware(mw),
		WithSystem("system prompt"),
		WithPrompt("user prompt"),
		WithDocs(doc),
		WithOutputType(map[string]string{"key": "value"}),
		WithOutputInstructions(""),
		WithCustomConstrainedOutput(),
		WithStreaming(streamFunc),
	}

	for _, opt := range options {
		if err := opt.applyGenerate(opts); err != nil {
			t.Fatalf("Failed to apply option: %v", err)
		}
	}

	returnToolRequests := true
	expected := &generateOptions{
		commonGenOptions: commonGenOptions{
			configOptions: configOptions{
				Config: &GenerationCommonConfig{Temperature: 0.7},
			},
			Model:              model,
			Tools:              []ToolRef{tool},
			ToolChoice:         ToolChoiceAuto,
			MaxTurns:           3,
			ReturnToolRequests: &returnToolRequests,
			Middleware:         []ModelMiddleware{mw},
		},
		promptingOptions: promptingOptions{
			SystemFn: opts.SystemFn,
			PromptFn: opts.PromptFn,
		},
		outputOptions: outputOptions{
			OutputFormat: OutputFormatJSON,
			OutputSchema: opts.OutputSchema,
			OutputInstructions: func() *string {
				s := ""
				return &s
			}(),
			CustomConstrained: true,
		},
		executionOptions: executionOptions{
			Stream: streamFunc,
		},
		documentOptions: documentOptions{
			Documents: []*Document{doc},
		},
	}

	if diff := cmp.Diff(expected, opts,
		cmpopts.IgnoreFields(commonGenOptions{}, "MessagesFn", "Middleware"),
		cmpopts.IgnoreFields(promptingOptions{}, "SystemFn", "PromptFn"),
		cmpopts.IgnoreFields(executionOptions{}, "Stream"),
		cmpopts.IgnoreUnexported(mockModel{}, mockTool{}),
		cmp.AllowUnexported(generateOptions{}, commonGenOptions{}, promptingOptions{},
			outputOptions{}, executionOptions{}, documentOptions{})); diff != "" {
		t.Errorf("Options not applied correctly, diff (-want +got):\n%s", diff)
	}

	if opts.MessagesFn == nil {
		t.Errorf("MessagesFn should not be nil")
	}
	if len(opts.Middleware) == 0 {
		t.Errorf("Middleware should not be empty")
	}
	if opts.SystemFn == nil {
		t.Errorf("SystemFn should not be nil")
	}
	if opts.PromptFn == nil {
		t.Errorf("PromptFn should not be nil")
	}
	if opts.Stream == nil {
		t.Errorf("Stream should not be nil")
	}
}
func TestPromptOptionsComplete(t *testing.T) {
	opts := &promptOptions{}

	mw := func(next ModelFunc) ModelFunc { return next }
	model := &mockModel{name: "test/model"}
	tool := &mockTool{name: "test/tool"}
	input := struct {
		Test string `json:"test"`
	}{
		Test: "value",
	}

	options := []PromptOption{
		WithModel(model),
		WithMessages(NewUserTextMessage("message")),
		WithConfig(&GenerationCommonConfig{Temperature: 0.7}),
		WithTools(tool),
		WithToolChoice(ToolChoiceAuto),
		WithMaxTurns(3),
		WithReturnToolRequests(true),
		WithMiddleware(mw),
		WithSystem("system prompt"),
		WithPrompt("user prompt"),
		WithDescription("test description"),
		WithMetadata(map[string]any{"key": "value"}),
		WithOutputType(map[string]string{"key": "value"}),
		WithOutputInstructions(""),
		WithCustomConstrainedOutput(),
		WithInputType(input),
	}

	for _, opt := range options {
		if err := opt.applyPrompt(opts); err != nil {
			t.Fatalf("Failed to apply option: %v", err)
		}
	}

	returnToolRequests := true
	expected := &promptOptions{
		commonGenOptions: commonGenOptions{
			configOptions: configOptions{
				Config: &GenerationCommonConfig{Temperature: 0.7},
			},
			Model:              model,
			Tools:              []ToolRef{tool},
			ToolChoice:         ToolChoiceAuto,
			MaxTurns:           3,
			ReturnToolRequests: &returnToolRequests,
			Middleware:         []ModelMiddleware{mw},
		},
		promptingOptions: promptingOptions{
			SystemFn: opts.SystemFn,
			PromptFn: opts.PromptFn,
		},
		inputOptions: inputOptions{
			InputSchema:  opts.InputSchema,
			DefaultInput: map[string]any{"test": "value"},
		},
		outputOptions: outputOptions{
			OutputFormat: OutputFormatJSON,
			OutputSchema: opts.OutputSchema,
			OutputInstructions: func() *string {
				s := ""
				return &s
			}(),
			CustomConstrained: true,
		},
		Description: "test description",
		Metadata:    map[string]any{"key": "value"},
	}

	if diff := cmp.Diff(expected, opts,
		cmpopts.IgnoreFields(commonGenOptions{}, "MessagesFn", "Middleware"),
		cmpopts.IgnoreFields(promptingOptions{}, "SystemFn", "PromptFn"),
		cmpopts.IgnoreFields(outputOptions{}, "OutputSchema"),
		cmpopts.IgnoreFields(inputOptions{}, "InputSchema"),
		cmpopts.IgnoreUnexported(mockModel{}, mockTool{}),
		cmp.AllowUnexported(promptOptions{}, commonGenOptions{}, promptingOptions{},
			inputOptions{}, outputOptions{})); diff != "" {
		t.Errorf("Options not applied correctly, diff (-want +got):\n%s", diff)
	}

	if opts.MessagesFn == nil {
		t.Errorf("MessagesFn should not be nil")
	}
	if len(opts.Middleware) == 0 {
		t.Errorf("Middleware should not be empty")
	}
	if opts.SystemFn == nil {
		t.Errorf("SystemFn should not be nil")
	}
	if opts.PromptFn == nil {
		t.Errorf("PromptFn should not be nil")
	}
	if opts.OutputSchema == nil {
		t.Errorf("OutputSchema should not be nil")
	}
	if opts.InputSchema == nil {
		t.Errorf("InputSchema should not be nil")
	}
}

func TestPromptExecuteOptionsComplete(t *testing.T) {
	opts := &promptExecutionOptions{}

	mw := func(next ModelFunc) ModelFunc { return next }
	model := &mockModel{name: "test/model"}
	tool := &mockTool{name: "test/tool"}
	streamFunc := func(context.Context, *ModelResponseChunk) error { return nil }
	input := map[string]string{"key": "value"}
	doc := DocumentFromText("doc", nil)

	options := []PromptExecuteOption{
		WithModel(model),
		WithMessages(NewUserTextMessage("message")),
		WithConfig(&GenerationCommonConfig{Temperature: 0.7}),
		WithTools(tool),
		WithToolChoice(ToolChoiceAuto),
		WithMaxTurns(3),
		WithReturnToolRequests(true),
		WithMiddleware(mw),
		WithDocs(doc),
		WithStreaming(streamFunc),
		WithInput(input),
	}

	for _, opt := range options {
		if err := opt.applyPromptExecute(opts); err != nil {
			t.Fatalf("Failed to apply option: %v", err)
		}
	}

	returnToolRequests := true
	expected := &promptExecutionOptions{
		commonGenOptions: commonGenOptions{
			configOptions: configOptions{
				Config: &GenerationCommonConfig{Temperature: 0.7},
			},
			Model:              model,
			Tools:              []ToolRef{tool},
			ToolChoice:         ToolChoiceAuto,
			MaxTurns:           3,
			ReturnToolRequests: &returnToolRequests,
			Middleware:         []ModelMiddleware{mw},
		},
		executionOptions: executionOptions{
			Stream: streamFunc,
		},
		documentOptions: documentOptions{
			Documents: []*Document{doc},
		},
		Input: input,
	}

	if diff := cmp.Diff(expected, opts,
		cmpopts.IgnoreFields(commonGenOptions{}, "MessagesFn", "Middleware"),
		cmpopts.IgnoreFields(executionOptions{}, "Stream"),
		cmpopts.IgnoreUnexported(mockModel{}, mockTool{}),
		cmp.AllowUnexported(promptExecutionOptions{}, commonGenOptions{},
			executionOptions{})); diff != "" {
		t.Errorf("Options not applied correctly, diff (-want +got):\n%s", diff)
	}

	if opts.MessagesFn == nil {
		t.Errorf("MessagesFn should not be nil")
	}
	if opts.Middleware == nil {
		t.Errorf("Middleware should not be nil")
	}
	if opts.Stream == nil {
		t.Errorf("Stream should not be nil")
	}
}

type mockModel struct {
	name string
}

func (m *mockModel) Name() string {
	return m.name
}

func (m *mockModel) Generate(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
	return nil, nil
}

type mockTool struct {
	name string
}

func (t *mockTool) Name() string {
	return t.name
}

func (t *mockTool) Definition() *ToolDefinition {
	return &ToolDefinition{Name: t.name}
}

func (t *mockTool) RunRaw(ctx context.Context, input any) (any, error) {
	return nil, nil
}

func TestWithInputTypeDefaultValues(t *testing.T) {
	t.Run("struct field values are captured as DefaultInput", func(t *testing.T) {
		type TestInput struct {
			Name    string  `json:"name"`
			Age     int     `json:"age"`
			Active  bool    `json:"active"`
			Balance float64 `json:"balance"`
		}

		input := TestInput{
			Name:    "John",
			Age:     30,
			Active:  true,
			Balance: 100.50,
		}

		opt := WithInputType(input).(*inputOptions)

		expectedDefaults := map[string]any{
			"name":    "John",
			"age":     float64(30),
			"active":  true,
			"balance": 100.50,
		}

		if diff := cmp.Diff(expectedDefaults, opt.DefaultInput); diff != "" {
			t.Errorf("DefaultInput mismatch (-want +got):\n%s", diff)
		}
	})

	t.Run("zero values are included in DefaultInput", func(t *testing.T) {
		type TestInput struct {
			Name   string `json:"name"`
			Count  int    `json:"count"`
			Active bool   `json:"active"`
		}

		input := TestInput{} // all zero values

		opt := WithInputType(input).(*inputOptions)

		expectedDefaults := map[string]any{
			"name":   "",
			"count":  float64(0),
			"active": false,
		}

		if diff := cmp.Diff(expectedDefaults, opt.DefaultInput); diff != "" {
			t.Errorf("DefaultInput should include zero values, diff (-want +got):\n%s", diff)
		}
	})

	t.Run("map input is used directly as DefaultInput", func(t *testing.T) {
		input := map[string]any{
			"name": "default",
			"age":  25,
		}

		opt := WithInputType(input).(*inputOptions)

		if diff := cmp.Diff(input, opt.DefaultInput); diff != "" {
			t.Errorf("DefaultInput should match map input, diff (-want +got):\n%s", diff)
		}
	})

	t.Run("jsonschema default tag is reflected in schema", func(t *testing.T) {
		type TestInputWithDefaults struct {
			Name   string `json:"name" jsonschema:"default=guest"`
			Age    int    `json:"age" jsonschema:"default=25"`
			Active bool   `json:"active" jsonschema:"default=true"`
		}

		opt := WithInputType(TestInputWithDefaults{}).(*inputOptions)

		props, ok := opt.InputSchema["properties"].(map[string]any)
		if !ok {
			t.Fatal("expected properties in schema")
		}

		nameSchema, ok := props["name"].(map[string]any)
		if !ok {
			t.Fatal("expected name property in schema")
		}
		if nameSchema["default"] != "guest" {
			t.Errorf("expected name default to be 'guest', got %v", nameSchema["default"])
		}

		ageSchema, ok := props["age"].(map[string]any)
		if !ok {
			t.Fatal("expected age property in schema")
		}
		if ageSchema["default"] != float64(25) {
			t.Errorf("expected age default to be 25, got %v", ageSchema["default"])
		}

		activeSchema, ok := props["active"].(map[string]any)
		if !ok {
			t.Fatal("expected active property in schema")
		}
		if activeSchema["default"] != true {
			t.Errorf("expected active default to be true, got %v", activeSchema["default"])
		}
	})

	t.Run("struct values take precedence over jsonschema defaults", func(t *testing.T) {
		type TestInputWithDefaults struct {
			Name string `json:"name" jsonschema:"default=guest"`
			Age  int    `json:"age" jsonschema:"default=25"`
		}

		input := TestInputWithDefaults{
			Name: "admin",
			Age:  40,
		}

		opt := WithInputType(input).(*inputOptions)

		// DefaultInput should have the struct values, not the jsonschema defaults
		expectedDefaults := map[string]any{
			"name": "admin",
			"age":  float64(40),
		}

		if diff := cmp.Diff(expectedDefaults, opt.DefaultInput); diff != "" {
			t.Errorf("struct values should be used as DefaultInput, diff (-want +got):\n%s", diff)
		}

		// But the schema should still have the jsonschema tag defaults
		props, ok := opt.InputSchema["properties"].(map[string]any)
		if !ok {
			t.Fatal("expected properties in schema")
		}

		nameSchema, ok := props["name"].(map[string]any)
		if !ok {
			t.Fatal("expected name property in schema")
		}
		if nameSchema["default"] != "guest" {
			t.Errorf("schema should retain jsonschema default 'guest', got %v", nameSchema["default"])
		}
	})
}
