// Copyright 2024 Google LLC
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
		opts    []CommonOption
		wantErr bool
	}{
		{
			name: "valid options",
			opts: []CommonOption{
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
			opts: []CommonOption{
				WithMessages(NewUserTextMessage("test")),
				WithMessagesFn(func(context.Context, any) ([]*Message, error) { return nil, nil }),
			},
			wantErr: true,
		},
		{
			name: "mutually exclusive - model",
			opts: []CommonOption{
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
			pgOpts := &promptGenerateOptions{}

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
				if err = opt.applyPromptGenerate(pgOpts); err != nil {
					t.Errorf("applyPromptGenerate() unexpected error = %v", err)
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
				WithSystemText("system instruction"),
				WithPromptText("user prompt"),
			},
			wantErr: false,
		},
		{
			name: "mutually exclusive - system",
			opts: []PromptingOption{
				WithSystemText("system instruction"),
				WithSystemFn(func(context.Context, any) (string, error) { return "system", nil }),
			},
			wantErr: true,
		},
		{
			name: "mutually exclusive - prompt",
			opts: []PromptingOption{
				WithPromptText("user prompt"),
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
				WithOutputInstructions(false),
			},
			wantErr: false,
		},
		{
			name: "duplicate options",
			opts: []OutputOption{
				WithOutputType(map[string]string{"key": "value"}),
				WithOutputFormat(OutputFormatText),
				WithOutputInstructions(false),
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

func TestExecutionOptions(t *testing.T) {
	tests := []struct {
		name    string
		opts    []ExecutionOption
		wantErr bool
	}{
		{
			name: "valid options",
			opts: []ExecutionOption{
				WithDocs(&Document{Content: []*Part{NewTextPart("test doc")}}),
				WithStreaming(func(context.Context, *ModelResponseChunk) error { return nil }),
			},
			wantErr: false,
		},
		{
			name: "duplicate - docs",
			opts: []ExecutionOption{
				WithDocs(&Document{Content: []*Part{NewTextPart("doc1")}}),
				WithDocs(&Document{Content: []*Part{NewTextPart("doc2")}}),
			},
			wantErr: true,
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
			pgOpts := &promptGenerateOptions{}

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
				if err = opt.applyPromptGenerate(pgOpts); err != nil {
					t.Errorf("applyPromptGenerate() unexpected error = %v", err)
					return
				}
			}
		})
	}
}

func TestPromptGenerateOptions(t *testing.T) {
	tests := []struct {
		name    string
		opts    []PromptGenerateOption
		wantErr bool
	}{
		{
			name: "valid options",
			opts: []PromptGenerateOption{
				WithInput(map[string]string{"key": "value"}),
			},
			wantErr: false,
		},
		{
			name: "duplicate - input",
			opts: []PromptGenerateOption{
				WithInput("input1"),
				WithInput("input2"),
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			opts := &promptGenerateOptions{}
			var err error
			for _, opt := range tt.opts {
				err = opt.applyPromptGenerate(opts)
				if err != nil {
					break
				}
			}
			if (err != nil) != tt.wantErr {
				t.Errorf("applyPromptGenerate() error = %v, wantErr %v", err, tt.wantErr)
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

	options := []GenerateOption{
		WithModel(model),
		WithMessages(NewUserTextMessage("message")),
		WithConfig(&GenerationCommonConfig{Temperature: 0.7}),
		WithTools(tool),
		WithToolChoice(ToolChoiceAuto),
		WithMaxTurns(3),
		WithReturnToolRequests(true),
		WithMiddleware(mw),
		WithSystemText("system prompt"),
		WithPromptText("user prompt"),
		WithDocs(DocumentFromText("doc", nil)),
		WithOutputType(map[string]string{"key": "value"}),
		WithOutputInstructions(true),
		WithStreaming(streamFunc),
	}

	for _, opt := range options {
		if err := opt.applyGenerate(opts); err != nil {
			t.Fatalf("Failed to apply option: %v", err)
		}
	}

	expected := &generateOptions{
		commonOptions: commonOptions{
			Model:                   model,
			Config:                  &GenerationCommonConfig{Temperature: 0.7},
			Tools:                   []Tool{tool},
			ToolChoice:              ToolChoiceAuto,
			MaxTurns:                3,
			ReturnToolRequests:      true,
			IsReturnToolRequestsSet: true,
			Middleware:              []ModelMiddleware{mw},
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
		},
		executionOptions: executionOptions{
			Documents: []*Document{DocumentFromText("doc", nil)},
			Stream:    streamFunc,
		},
	}

	if diff := cmp.Diff(expected, opts,
		cmpopts.IgnoreFields(commonOptions{}, "MessagesFn", "Middleware"),
		cmpopts.IgnoreFields(promptingOptions{}, "SystemFn", "PromptFn"),
		cmpopts.IgnoreFields(executionOptions{}, "Stream"),
		cmpopts.IgnoreUnexported(mockModel{}, mockTool{}),
		cmp.AllowUnexported(generateOptions{}, commonOptions{}, promptingOptions{},
			outputOptions{}, executionOptions{})); diff != "" {
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
		WithSystemText("system prompt"),
		WithPromptText("user prompt"),
		WithDescription("test description"),
		WithMetadata(map[string]any{"key": "value"}),
		WithOutputType(map[string]string{"key": "value"}),
		WithOutputInstructions(true),
		WithInputType(input),
	}

	for _, opt := range options {
		if err := opt.applyPrompt(opts); err != nil {
			t.Fatalf("Failed to apply option: %v", err)
		}
	}

	expected := &promptOptions{
		commonOptions: commonOptions{
			Model:                   model,
			Config:                  &GenerationCommonConfig{Temperature: 0.7},
			Tools:                   []Tool{tool},
			ToolChoice:              ToolChoiceAuto,
			MaxTurns:                3,
			ReturnToolRequests:      true,
			IsReturnToolRequestsSet: true,
			Middleware:              []ModelMiddleware{mw},
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
		},
		Description:  "test description",
		Metadata:     map[string]any{"key": "value"},
		InputSchema:  opts.InputSchema,
		DefaultInput: map[string]any{"test": "value"},
	}

	if diff := cmp.Diff(expected, opts,
		cmpopts.IgnoreFields(commonOptions{}, "MessagesFn", "Middleware"),
		cmpopts.IgnoreFields(promptingOptions{}, "SystemFn", "PromptFn"),
		cmpopts.IgnoreFields(outputOptions{}, "OutputSchema"),
		cmpopts.IgnoreFields(promptOptions{}, "InputSchema"),
		cmpopts.IgnoreUnexported(mockModel{}, mockTool{}),
		cmp.AllowUnexported(promptOptions{}, commonOptions{}, promptingOptions{},
			outputOptions{})); diff != "" {
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

func TestPromptGenerateOptionsComplete(t *testing.T) {
	opts := &promptGenerateOptions{}

	mw := func(next ModelFunc) ModelFunc { return next }
	model := &mockModel{name: "test/model"}
	tool := &mockTool{name: "test/tool"}
	streamFunc := func(context.Context, *ModelResponseChunk) error { return nil }
	input := map[string]string{"key": "value"}
	doc := DocumentFromText("doc", nil)

	options := []PromptGenerateOption{
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
		if err := opt.applyPromptGenerate(opts); err != nil {
			t.Fatalf("Failed to apply option: %v", err)
		}
	}

	expected := &promptGenerateOptions{
		commonOptions: commonOptions{
			Model:                   model,
			Config:                  &GenerationCommonConfig{Temperature: 0.7},
			Tools:                   []Tool{tool},
			ToolChoice:              ToolChoiceAuto,
			MaxTurns:                3,
			ReturnToolRequests:      true,
			IsReturnToolRequestsSet: true,
			Middleware:              []ModelMiddleware{mw},
		},
		executionOptions: executionOptions{
			Documents: []*Document{doc},
			Stream:    streamFunc,
		},
		Input: input,
	}

	if diff := cmp.Diff(expected, opts,
		cmpopts.IgnoreFields(commonOptions{}, "MessagesFn", "Middleware"),
		cmpopts.IgnoreFields(executionOptions{}, "Stream"),
		cmpopts.IgnoreUnexported(mockModel{}, mockTool{}),
		cmp.AllowUnexported(promptGenerateOptions{}, commonOptions{},
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

func (t *mockTool) Definition() *ToolDefinition {
	return &ToolDefinition{Name: t.name}
}

func (t *mockTool) RunRaw(ctx context.Context, input any) (any, error) {
	return nil, nil
}
