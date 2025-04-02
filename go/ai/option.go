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
	"encoding/json"
	"errors"
	"fmt"

	"github.com/firebase/genkit/go/internal/base"
	"github.com/invopop/jsonschema"
)

// promptFn is a function that generates a prompt.
type promptFn = func(context.Context, any) (string, error)

// messagesFn is a function that generates messages.
type messagesFn = func(context.Context, any) ([]*Message, error)

// commonOptions are common options for model generation, prompt definition, and prompt execution.
type commonOptions struct {
	ModelArg                ModelArg          // New preferred field
	ModelName               string            // Name of model to use
	MessagesFn              messagesFn        // Messages function. If this is set, Messages should be an empty.
	Config                  any               // Model configuration. If nil will be taken from the prompt config.
	Tools                   []ToolRef         // References to tools to use.
	ToolChoice              ToolChoice        // Whether tool calls are required, disabled, or optional.
	MaxTurns                int               // Maximum number of tool call iterations.
	ReturnToolRequests      bool              // Whether to return tool requests instead of making the tool calls and continuing the generation.
	IsReturnToolRequestsSet bool              // Whether the ReturnToolRequests field was set (false is not enough information as to whether to override).
	Middleware              []ModelMiddleware // Middleware to apply to the model request.
}

type CommonOption interface {
	applyCommon(*commonOptions) error
	applyPrompt(*promptOptions) error
	applyGenerate(*generateOptions) error
	applyPromptGenerate(*promptGenerateOptions) error
}

// applyCommon applies the option to the common options.
func (o *commonOptions) applyCommon(opts *commonOptions) error {
	if o.MessagesFn != nil {
		if opts.MessagesFn != nil {
			return errors.New("cannot set messages more than once (either WithMessages or WithMessagesFn)")
		}
		opts.MessagesFn = o.MessagesFn
	}

	if o.ModelArg != nil {
		if opts.ModelArg != nil || opts.ModelName != "" {
			return errors.New("cannot set model more than once (either WithModel or WithModelName)")
		}
		opts.ModelArg = o.ModelArg
		return nil
	}

	if o.ModelName != "" {
		if opts.ModelArg != nil || opts.ModelName != "" {
			return errors.New("cannot set model more than once (either WithModel or WithModelName)")
		}
		opts.ModelName = o.ModelName
	}

	if o.Config != nil {
		if opts.Config != nil {
			return errors.New("cannot set config more than once (WithConfig)")
		}
		opts.Config = o.Config
	}

	if o.Tools != nil {
		if opts.Tools != nil {
			return errors.New("cannot set tools more than once (WithTools)")
		}
		opts.Tools = o.Tools
	}

	if o.ToolChoice != "" {
		if opts.ToolChoice != "" {
			return errors.New("cannot set tool choice more than once (WithToolChoice)")
		}
		opts.ToolChoice = o.ToolChoice
	}

	if o.MaxTurns > 0 {
		if opts.MaxTurns > 0 {
			return errors.New("cannot set max turns more than once (WithMaxTurns)")
		}
		opts.MaxTurns = o.MaxTurns
	}

	if o.IsReturnToolRequestsSet {
		if opts.IsReturnToolRequestsSet {
			return errors.New("cannot configure returning tool requests more than once (WithReturnToolRequests)")
		}
		opts.ReturnToolRequests = o.ReturnToolRequests
		opts.IsReturnToolRequestsSet = true
	}

	if o.Middleware != nil {
		if opts.Middleware != nil {
			return errors.New("cannot set middleware more than once (WithMiddleware)")
		}
		opts.Middleware = o.Middleware
	}

	return nil
}

// applyPromptGenerate applies the option to the prompt request options.
func (o *commonOptions) applyPromptGenerate(reqOpts *promptGenerateOptions) error {
	return o.applyCommon(&reqOpts.commonOptions)
}

// applyPrompt applies the option to the prompt options.
func (o *commonOptions) applyPrompt(pOpts *promptOptions) error {
	return o.applyCommon(&pOpts.commonOptions)
}

// applyGenerate applies the option to the generate options.
func (o *commonOptions) applyGenerate(genOpts *generateOptions) error {
	return o.applyCommon(&genOpts.commonOptions)
}

// WithMessages sets the messages.
// These messages will be sandwiched between the system and user messages.
func WithMessages(messages ...*Message) CommonOption {
	return &commonOptions{
		MessagesFn: func(ctx context.Context, _ any) ([]*Message, error) {
			return messages, nil
		},
	}
}

// WithMessagesFn sets the request messages to the result of the function.
// These messages will be sandwiched between the system and user messages.
func WithMessagesFn(fn messagesFn) CommonOption {
	return &commonOptions{MessagesFn: fn}
}

// WithTools sets the tools to use for the generate request.
// Tools cannot be combined with WithToolChoice(ToolChoiceNone).
func WithTools(tools ...ToolRef) CommonOption {
	return &commonOptions{Tools: tools}
}

// WithConfig sets the model configuration.
func WithConfig(config any) CommonOption {
	return &commonOptions{Config: config}
}

// WithModel sets a resolvable model reference to use for generation.
func WithModel(model ModelArg) CommonOption {
	return &commonOptions{ModelArg: model}
}

// WithModelName sets the model name to call for generation.
// The model name will be resolved to a Model and may error if the reference is invalid.
func WithModelName(name string) CommonOption {
	return &commonOptions{ModelName: name}
}

// WithMiddleware sets middleware to apply to the model request.
func WithMiddleware(middleware ...ModelMiddleware) CommonOption {
	return &commonOptions{Middleware: middleware}
}

// WithMaxTurns sets the maximum number of tool call iterations before erroring.
// A tool call happens when tools are provided in the request and a model decides to call one or more as a response.
// Each round trip, including multiple tools in parallel, counts as one turn.
func WithMaxTurns(maxTurns int) CommonOption {
	return &commonOptions{MaxTurns: maxTurns}
}

// WithReturnToolRequests configures whether to return tool requests instead of making the tool calls and continuing the generation.
func WithReturnToolRequests(returnReqs bool) CommonOption {
	return &commonOptions{
		ReturnToolRequests:      returnReqs,
		IsReturnToolRequestsSet: true,
	}
}

// WithToolChoice configures whether by default tool calls are required, disabled, or optional for the prompt.
func WithToolChoice(toolChoice ToolChoice) CommonOption {
	return &commonOptions{ToolChoice: toolChoice}
}

// promptOptions are options for defining a prompt.
type promptOptions struct {
	commonOptions
	promptingOptions
	outputOptions
	Description  string             // Description of the prompt.
	InputSchema  *jsonschema.Schema // Schema of the input.
	DefaultInput map[string]any     // Default input that will be used if no input is provided.
	Metadata     map[string]any     // Arbitrary metadata.
}

// PromptOption is an option for defining a prompt.
// It applies only to DefinePrompt().
type PromptOption interface {
	applyPrompt(*promptOptions) error
}

// applyPrompt applies the option to the prompt options.
func (o *promptOptions) applyPrompt(opts *promptOptions) error {
	if err := o.commonOptions.applyPrompt(opts); err != nil {
		return err
	}

	if err := o.promptingOptions.applyPrompt(opts); err != nil {
		return err
	}

	if err := o.outputOptions.applyPrompt(opts); err != nil {
		return err
	}

	if o.Description != "" {
		if opts.Description != "" {
			return errors.New("cannot set description more than once (WithDescription)")
		}
		opts.Description = o.Description
	}

	if o.InputSchema != nil {
		if opts.InputSchema != nil {
			return errors.New("cannot set input schema more than once (WithInputType)")
		}
		opts.InputSchema = o.InputSchema
	}

	if o.DefaultInput != nil {
		if opts.DefaultInput != nil {
			return errors.New("cannot set default input more than once (WithInputType)")
		}
		opts.DefaultInput = o.DefaultInput
	}

	if o.Metadata != nil {
		if opts.Metadata != nil {
			return errors.New("cannot set metadata more than once (WithMetadata)")
		}
		opts.Metadata = o.Metadata
	}

	return nil
}

// WithDescription sets the description of the prompt.
func WithDescription(description string) PromptOption {
	return &promptOptions{Description: description}
}

// WithMetadata sets arbitrary metadata for the prompt.
func WithMetadata(metadata map[string]any) PromptOption {
	return &promptOptions{Metadata: metadata}
}

// WithInputType uses the type provided to derive the input schema.
// The inputted value will serve as the default input if no input is given at generation time.
// Only supports structs and map[string]any types.
func WithInputType(input any) PromptOption {
	var defaultInput map[string]any

	switch v := input.(type) {
	case map[string]any:
		defaultInput = v
	default:
		data, err := json.Marshal(input)
		if err != nil {
			panic(fmt.Errorf("failed to marshal default input (WithInputType): %w", err))
		}

		err = json.Unmarshal(data, &defaultInput)
		if err != nil {
			panic(fmt.Errorf("type %T is not supported, only structs and map[string]any are supported (WithInputType)", input))
		}
	}

	return &promptOptions{
		InputSchema:  base.InferJSONSchema(input),
		DefaultInput: defaultInput,
	}
}

// promptingOptions are options for the system and user prompts of a prompt or generate request.
type promptingOptions struct {
	SystemFn promptFn // Function to generate the system prompt.
	PromptFn promptFn // Function to generate the user prompt.
}

// PromptingOption is an option for the system and user prompts of a prompt or generate request.
// It applies only to DefinePrompt() and Generate().
type PromptingOption interface {
	applyPrompting(*promptingOptions) error
	applyPrompt(*promptOptions) error
	applyGenerate(*generateOptions) error
}

// applyPrompting applies the option to the prompting options.
func (o *promptingOptions) applyPrompting(opts *promptingOptions) error {
	if o.SystemFn != nil {
		if opts.SystemFn != nil {
			return errors.New("cannot set system text more than once (either WithSystemText or WithSystemFn)")
		}
		opts.SystemFn = o.SystemFn
	}

	if o.PromptFn != nil {
		if opts.PromptFn != nil {
			return errors.New("cannot set prompt more than once (either WithPromptText or WithPromptFn)")
		}
		opts.PromptFn = o.PromptFn
	}

	return nil
}

// applyPrompt applies the option to the prompt options.
func (o *promptingOptions) applyPrompt(opts *promptOptions) error {
	return o.applyPrompting(&opts.promptingOptions)
}

// applyGenerate applies the option to the generate options.
func (o *promptingOptions) applyGenerate(opts *generateOptions) error {
	return o.applyPrompting(&opts.promptingOptions)
}

// WithSystemText sets the system prompt message.
// The system prompt is always the first message in the list.
func WithSystemText(text string) PromptingOption {
	return &promptingOptions{
		SystemFn: func(ctx context.Context, _ any) (string, error) {
			return text, nil
		},
	}
}

// WithSystemFn sets the function that generates the system prompt message.
// The system prompt is always the first message in the list.
func WithSystemFn(fn promptFn) PromptingOption {
	return &promptingOptions{SystemFn: fn}
}

// WithPromptText sets the user prompt message.
// The user prompt is always the last message in the list.
func WithPromptText(text string) PromptingOption {
	return &promptingOptions{
		PromptFn: func(ctx context.Context, _ any) (string, error) {
			return text, nil
		},
	}
}

// WithPromptFn sets the function that generates the user prompt message.
// The user prompt is always the last message in the list.
func WithPromptFn(fn promptFn) PromptingOption {
	return &promptingOptions{PromptFn: fn}
}

// outputOptions are options for the output of a prompt or generate request.
type outputOptions struct {
	OutputSchema map[string]any // JSON schema of the output.
	OutputFormat OutputFormat   // Format of the output. If OutputSchema is set, this is set to OutputFormatJSON.
}

// OutputOption is an option for the output of a prompt or generate request.
// It applies only to DefinePrompt() and Generate().
type OutputOption interface {
	applyOutput(*outputOptions) error
	applyPrompt(*promptOptions) error
	applyGenerate(*generateOptions) error
}

// applyOutput applies the option to the output options.
func (o *outputOptions) applyOutput(opts *outputOptions) error {
	if o.OutputSchema != nil {
		if opts.OutputSchema != nil {
			return errors.New("cannot set output schema more than once (WithOutputType)")
		}
		opts.OutputSchema = o.OutputSchema
	}

	if o.OutputFormat != "" {
		if opts.OutputFormat != "" && opts.OutputFormat != o.OutputFormat {
			return errors.New("cannot set output format more than once (WithOutputFormat)")
		}
		opts.OutputFormat = o.OutputFormat
	}

	return nil
}

// applyPrompt applies the option to the prompt options.
func (o *outputOptions) applyPrompt(pOpts *promptOptions) error {
	return o.applyOutput(&pOpts.outputOptions)
}

// applyGenerate applies the option to the generate options.
func (o *outputOptions) applyGenerate(genOpts *generateOptions) error {
	return o.applyOutput(&genOpts.outputOptions)
}

// WithOutputType sets the schema and format of the output based on the value provided.
func WithOutputType(output any) OutputOption {
	return &outputOptions{
		OutputSchema: base.SchemaAsMap(base.InferJSONSchema(output)),
		OutputFormat: OutputFormatJSON,
	}
}

// WithOutputFormat sets the format of the output.
func WithOutputFormat(format OutputFormat) OutputOption {
	return &outputOptions{OutputFormat: format}
}

// executionOptions are options for the execution of a prompt or generate request.
type executionOptions struct {
	Documents []*Document         // Docs to pass to the model as context.
	Stream    ModelStreamCallback // Function to call with each chunk of the generated response.
}

// ExecutionOption is an option for the execution of a prompt or generate request. It applies only to Generate() and prompt.Execute().
type ExecutionOption interface {
	applyExecution(*executionOptions) error
	applyGenerate(*generateOptions) error
	applyPromptGenerate(*promptGenerateOptions) error
}

// applyExecution applies the option to the runtime options.
func (o *executionOptions) applyExecution(execOpts *executionOptions) error {
	if o.Documents != nil {
		if execOpts.Documents != nil {
			return errors.New("cannot set context more than once (WithDocs)")
		}
		execOpts.Documents = o.Documents
	}

	if o.Stream != nil {
		if execOpts.Stream != nil {
			return errors.New("cannot set stream callback more than once (WithStream)")
		}
		execOpts.Stream = o.Stream
	}

	return nil
}

// applyGenerate applies the option to the generate options.
func (o *executionOptions) applyGenerate(genOpts *generateOptions) error {
	return o.applyExecution(&genOpts.executionOptions)
}

// applyPromptGenerate applies the option to the prompt request options.
func (o *executionOptions) applyPromptGenerate(genOpts *promptGenerateOptions) error {
	return o.applyExecution(&genOpts.executionOptions)
}

// WithDocs sets the retrieved documents to be used as context for the generate request.
func WithDocs(docs ...*Document) ExecutionOption {
	return &executionOptions{Documents: docs}
}

// WithStreaming sets the stream callback for the generate request.
// A callback is a function that is called with each chunk of the generated response before the final response is returned.
func WithStreaming(callback ModelStreamCallback) ExecutionOption {
	return &executionOptions{Stream: callback}
}

// generateOptions are options for generating a model response by calling a model directly.
type generateOptions struct {
	commonOptions
	promptingOptions
	outputOptions
	executionOptions
}

// GenerateOption is an option for generating a model response. It applies only to Generate().
type GenerateOption interface {
	applyGenerate(*generateOptions) error
}

// applyGenerate applies the option to the generate options.
func (o *generateOptions) applyGenerate(genOpts *generateOptions) error {
	if err := o.commonOptions.applyGenerate(genOpts); err != nil {
		return err
	}

	if err := o.promptingOptions.applyGenerate(genOpts); err != nil {
		return err
	}

	if err := o.outputOptions.applyGenerate(genOpts); err != nil {
		return err
	}

	if err := o.executionOptions.applyGenerate(genOpts); err != nil {
		return err
	}

	return nil
}

// promptGenerateOptions are options for generating a model response by executing a prompt.
type promptGenerateOptions struct {
	commonOptions
	executionOptions
	Input any // Input fields for the prompt. If not nil this should be a struct that matches the prompt's input schema.
}

// PromptGenerateOption is an option for executing a prompt. It applies only to prompt.Execute().
type PromptGenerateOption interface {
	applyPromptGenerate(*promptGenerateOptions) error
}

// applyPromptGenerate applies the option to the prompt request options.
func (o *promptGenerateOptions) applyPromptGenerate(reqOpts *promptGenerateOptions) error {
	if err := o.commonOptions.applyPromptGenerate(reqOpts); err != nil {
		return err
	}

	if err := o.executionOptions.applyPromptGenerate(reqOpts); err != nil {
		return err
	}

	if reqOpts.Input != nil {
		return errors.New("cannot set input more than once (WithInput)")
	}
	reqOpts.Input = o.Input

	return nil
}

// WithInput sets the input for the prompt request.
func WithInput(input any) PromptGenerateOption {
	return &promptGenerateOptions{Input: input}
}
