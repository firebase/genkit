// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"

	"github.com/firebase/genkit/go/internal/base"
	"github.com/invopop/jsonschema"
)

// promptFn is a function that generates a prompt.
type promptFn = func(context.Context, any) (string, error)

// messagesFn is a function that generates messages.
type messagesFn = func(context.Context, any) ([]*Message, error)

// renderFn is a function that renders a prompt intoa model request.
type renderFn = func(context.Context, any) (*ModelRequest, error)

// commonOptions are common options for model generation, prompt definition, and prompt execution.
type commonOptions struct {
	ModelName               string                  // Name of the model to use.
	Model                   Model                   // Model to use.
	MessagesFn              messagesFn              // Messages function. If this is set, Messages should be an empty.
	Config                  *GenerationCommonConfig // Model configuration. If nil will be taken from the prompt config.
	Tools                   []Tool                  // Tools to use.
	ToolChoice              ToolChoice              // Whether tool calls are required, disabled, or optional.
	MaxTurns                int                     // Maximum number of tool call iterations.
	ReturnToolRequests      bool                    // Whether to return tool requests instead of making the tool calls and continuing the generation.
	IsReturnToolRequestsSet bool                    // Whether the ReturnToolRequests field was set (false is not enough information as to whether to override).
}

type CommonOption interface {
	applyCommon(*commonOptions) error
	applyPrompt(*promptOptions) error
	applyGenerate(*generateOptions) error
	applyPromptRequest(*promptGenerateOptions) error
}

// applyCommon applies the option to the common options.
func (o *commonOptions) applyCommon(opts *commonOptions) error {
	if o.MessagesFn != nil {
		if opts.MessagesFn != nil {
			return errors.New("cannot set messages more than once (either WithMessages or WithMessagesFn)")
		}
		opts.MessagesFn = o.MessagesFn
	}

	if o.Model != nil {
		if opts.Model != nil || opts.ModelName != "" {
			return errors.New("cannot set model more than once (either WithModel or WithModelName)")
		}
		opts.Model = o.Model
	}

	if o.ModelName != "" {
		if opts.Model != nil || opts.ModelName != "" {
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

	return nil
}

// applyPromptRequest applies the option to the prompt request options.
func (o *commonOptions) applyPromptRequest(reqOpts *promptGenerateOptions) error {
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
func WithTools(tools ...Tool) CommonOption {
	return &commonOptions{Tools: tools}
}

// WithConfig sets the model configuration.
func WithConfig(config *GenerationCommonConfig) CommonOption {
	return &commonOptions{Config: config}
}

// WithModel sets the model to call for generation.
func WithModel(model Model) CommonOption {
	return &commonOptions{Model: model}
}

// WithModelName sets the model name to call for generation.
// The model name will be resolved to a Model and may error if the reference is invalid.
func WithModelName(name string) CommonOption {
	return &commonOptions{ModelName: name}
}

// WithMaxTurns sets the maximum number of tool call iterations before erroring.
// A tool call happens when tools are provided in the request and a model decides to call one or more as a response.
// Each round trip, including multiple tools in parallel, counts as one turn.
func WithMaxTurns(maxTurns int) CommonOption {
	if maxTurns <= 0 {
		panic(fmt.Errorf("maxTurns must be greater than 0, got %d", maxTurns))
	}
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
	InputSchema  *jsonschema.Schema // Schema of the input.
	DefaultInput map[string]any     // Default input that will be used if no input is provided.
	RenderFn     renderFn           // Function to render the prompt.
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

	if err := o.outputOptions.applyPrompt(opts); err != nil {
		return err
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

	if o.RenderFn != nil {
		if opts.RenderFn != nil {
			return errors.New("cannot set render function more than once (WithRenderFn)")
		}
		opts.RenderFn = o.RenderFn
	}

	if o.Metadata != nil {
		if opts.Metadata != nil {
			return errors.New("cannot set metadata more than once (WithMetadata)")
		}
		opts.Metadata = o.Metadata
	}

	return nil
}

// WithRenderFn sets the function to render the prompt.
func WithRenderFn(fn renderFn) PromptOption {
	return &promptOptions{RenderFn: fn}
}

// WithMetadata sets arbitrary metadata for the prompt.
func WithMetadata(metadata map[string]any) PromptOption {
	return &promptOptions{Metadata: metadata}
}

// WithInputType uses the type provided to derive the input schema.
// The inputted value will serve as the default input if no input is given at generation time.
func WithInputType(input any) *promptOptions {
	// TODO: Switch case is incomplete and neither covers all types nor is opinionated.

	var defaultInput map[string]any
	switch v := input.(type) {
	case bool:
		defaultInput = map[string]any{"value": strconv.FormatBool(v)}
	case int:
		defaultInput = map[string]any{"value": strconv.Itoa(v)}
	case float32:
		defaultInput = map[string]any{"value": fmt.Sprintf("%f", v)}
	case float64:
		defaultInput = map[string]any{"value": fmt.Sprintf("%f", v)}
	case string:
		defaultInput = map[string]any{"value": v}
	case []any:
		defaultInput = map[string]any{"value": v}
	case map[string]any:
		defaultInput = v
	default:
		// Structs.
	}

	data, err := json.Marshal(defaultInput)
	if err != nil {
		panic(fmt.Errorf("failed to marshal default input (WithInputType): %w", err))
	}

	err = json.Unmarshal(data, &defaultInput)
	if err != nil {
		panic(fmt.Errorf("failed to unmarshal default input (WithInputType): %w", err))
	}

	return &promptOptions{
		InputSchema:  base.InferJSONSchemaNonReferencing(input),
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
	applyPrompt(*promptOptions) error
	applyGenerate(*generateOptions) error
}

// applyPrompt applies the option to the prompt options.
func (o *outputOptions) applyPrompt(opts *promptOptions) error {
	if opts.OutputSchema != nil || opts.OutputFormat != "" {
		return errors.New("cannot set output options more than once (WithOutputType)")
	}
	opts.outputOptions = *o

	return nil
}

// applyGenerate applies the option to the generate options.
func (o *outputOptions) applyGenerate(opts *generateOptions) error {
	if opts.OutputSchema != nil || opts.OutputFormat != "" {
		return errors.New("cannot set output options more than once (WithOutputType)")
	}
	opts.outputOptions = *o

	return nil
}

// WithOutputType sets the schema and format of the output based on the value provided.
func WithOutputType(output any) OutputOption {
	// TODO: Does OutputSchema need to be a map?
	return &outputOptions{
		OutputSchema: base.SchemaAsMap(base.InferJSONSchemaNonReferencing(output)),
		OutputFormat: OutputFormatJSON,
	}
}

// WithOutputFormat sets the format of the output.
func WithOutputFormat(format OutputFormat) OutputOption {
	return &outputOptions{OutputFormat: format}
}

// executionOptions are options for the execution of a prompt or generate request.
type executionOptions struct {
	Context    []*Document         // Context to pass to model, if any.
	Middleware []ModelMiddleware   // Middleware to apply to the generation.
	Stream     ModelStreamCallback // Function to call with each chunk of the generated response.
}

// ExecutionOption is an option for the execution of a prompt or generate request. It applies only to Generate() and prompt.Execute().
type ExecutionOption interface {
	applyRuntime(*executionOptions) error
	applyGenerate(*generateOptions) error
	applyPromptRequest(*promptGenerateOptions) error
}

// applyRuntime applies the option to the runtime options.
func (o *executionOptions) applyRuntime(runOpts *executionOptions) error {
	if o.Context != nil {
		if runOpts.Context != nil {
			return errors.New("cannot set context more than once (WithContext)")
		}
		runOpts.Context = o.Context
	}

	if o.Middleware != nil {
		if runOpts.Middleware != nil {
			return errors.New("cannot set middleware more than once (WithMiddleware)")
		}
		runOpts.Middleware = o.Middleware
	}

	if o.Stream != nil {
		if runOpts.Stream != nil {
			return errors.New("cannot set stream callback more than once (WithStream)")
		}
		runOpts.Stream = o.Stream
	}

	return nil
}

// applyGenerate applies the option to the generate options.
func (o *executionOptions) applyGenerate(genOpts *generateOptions) error {
	return o.applyRuntime(&genOpts.executionOptions)
}

// applyPromptRequest applies the option to the prompt request options.
func (o *executionOptions) applyPromptRequest(reqOpts *promptGenerateOptions) error {
	return o.applyRuntime(&reqOpts.executionOptions)
}

// WithContext sets the retrieved documents to be used as context for the generate request.
func WithContext(docs ...*Document) ExecutionOption {
	return &executionOptions{Context: docs}
}

// WithMiddleware sets middleware to apply to the model request.
func WithMiddleware(middleware ...ModelMiddleware) ExecutionOption {
	return &executionOptions{Middleware: middleware}
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

// PromptRequestOption is an option for executing a prompt. It applies only to prompt.Execute().
type PromptRequestOption interface {
	applyPromptRequest(*promptGenerateOptions) error
}

// applyPromptRequest applies the option to the prompt request options.
func (o *promptGenerateOptions) applyPromptRequest(reqOpts *promptGenerateOptions) error {
	if err := o.commonOptions.applyPromptRequest(reqOpts); err != nil {
		return err
	}

	if err := o.executionOptions.applyPromptRequest(reqOpts); err != nil {
		return err
	}

	if reqOpts.Input != nil {
		return errors.New("cannot set input more than once (WithInput)")
	}
	reqOpts.Input = o.Input

	return nil
}

// WithInput sets the input for the prompt request.
func WithInput(input any) PromptRequestOption {
	return &promptGenerateOptions{Input: input}
}
