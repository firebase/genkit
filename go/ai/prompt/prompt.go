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

package prompt

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"

	"github.com/aymerick/raymond"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/invopop/jsonschema"
)

type Prompt struct {
	registry    *registry.Registry
	action      core.ActionDef[any, *ai.ModelRequest, struct{}]
	Name        string // The name of the prompt.
	Description string // Prompt description.
	Config
	Template     *raymond.Template // The parsed prompt template.
	TemplateText string            // The original prompt template text.
}

// Config is optional configuration for a [Prompt].
type Config struct {
	Variant            string                     // The prompt variant.
	ModelName          string                     // The name of the model for which the prompt is input. If this is non-empty, Model should be nil.
	Model              ai.Model                   // The Model to use. If this is set, ModelName should be an empty string.
	System             string                     // The System prompt. If this is non-empty, SystemFn should be nil.
	SystemFn           PromptFn                   // The System prompt function. If this is set, System should be an empty string.
	Prompt             string                     // The User prompt. If this is non-empty, PromptFn should be nil.
	PromptFn           PromptFn                   // The User prompt function. If this is set, Prompt should be an empty string.
	Messages           []*ai.Message              // The messages to add to the prompt. If this is set, MessagesFn should be an empty.
	MessagesFn         MessagesFn                 // The messages function. If this is set, Messages should be an empty.
	RenderFn           RenderFn                   // Override the render function.
	Tools              []ai.Tool                  // The tools to use.
	GenerationConfig   *ai.GenerationCommonConfig // Details for the model.
	InputSchema        *jsonschema.Schema         // Schema for input variables.
	DefaultInput       map[string]any             // Default input variable values.
	OutputFormat       ai.OutputFormat            // Desired output format.
	OutputSchema       *jsonschema.Schema         // Desired output schema, for JSON output.
	Metadata           map[string]any             // Arbitrary metadata.
	ToolChoice         ai.ToolChoice              // ToolChoice is the tool choice to use.
	MaxTurns           int                        // MaxTurns is the maximum number of turns.
	ReturnToolRequests bool                       // ReturnToolRequests is whether to return tool requests.
}

type PromptFn = func(context.Context, any) (string, error)
type MessagesFn = func(context.Context, any) ([]*ai.Message, error)
type RenderFn = func(ctx context.Context, input any) (*ai.ModelRequest, error)

// PromptOption configures params for the prompt.
type PromptOption = func(p *Prompt) error

// Define creates and registers a new Prompt.
func Define(r *registry.Registry, provider, name string, opts ...PromptOption) (*Prompt, error) {
	p := &Prompt{
		registry: r,
	}

	for _, with := range opts {
		err := with(p)
		if err != nil {
			return nil, err
		}
	}

	if p.ModelName != "" && p.Model != nil {
		return nil, errors.New("prompt.Define: config must specify exactly one of ModelName and Model")
	}

	if p.Variant != "" {
		name += "." + p.Variant
	}

	renderFn := p.buildRequest
	if p.Config.RenderFn != nil {
		renderFn = p.Config.RenderFn
	}

	// TODO: Undo clearing of the Version once Monaco Editor supports newer than JSON schema draft-07.
	if p.InputSchema != nil {
		p.InputSchema.Version = ""
	}

	metadata := map[string]any{
		"prompt": map[string]any{
			"name":     p.Name,
			"input":    map[string]any{"schema": p.InputSchema},
			"output":   map[string]any{"format": p.OutputFormat},
			"template": p.TemplateText,
		},
	}

	p.action = *core.DefineActionWithInputSchema(r, provider, name, atype.Prompt, metadata, p.Config.InputSchema, renderFn)
	return p, nil
}

// Render renders the prompt template based on user input.
func (p *Prompt) Render(ctx context.Context, input any) (*ai.ModelRequest, error) {
	if p == nil {
		return nil, errors.New("prompt.Render: called on a nil Prompt; check that all prompts are defined")
	}
	return p.action.Run(ctx, input, nil)
}

// IsDefinedPrompt reports whether a [Prompt] is defined.
func IsDefinedPrompt(r *registry.Registry, provider, name string) bool {
	return LookupPrompt(r, provider, name) != nil
}

// LookupPrompt looks up a [Prompt] registered by [DefinePrompt].
// It returns nil if the prompt was not defined.
func LookupPrompt(r *registry.Registry, provider, name string) *Prompt {
	action := core.LookupActionFor[any, *ai.ModelRequest, struct{}](r, atype.Prompt, provider, name)
	p := &Prompt{
		action: *action,
	}
	return p
}

// WithSystemText adds system message to the prompt.
func WithSystemText(systemText string) PromptOption {
	return func(p *Prompt) error {
		if p.SystemFn != nil || p.System != "" {
			return errors.New("prompt.WithSystemText: cannot set system text more than once")
		}
		p.System = systemText

		return nil
	}
}

// WithSystemFn sets the result of the callback function as system message on the prompt.
func WithSystemFn(systemFn PromptFn) PromptOption {
	return func(p *Prompt) error {
		if p.SystemFn != nil || p.System != "" {
			return errors.New("prompt.WithSystemFn: cannot set system text more than once")
		}
		p.SystemFn = systemFn

		return nil
	}
}

// WithPromptText adds user message to the prompt.
func WithPromptText(promptText string) PromptOption {
	return func(p *Prompt) error {
		if p.PromptFn != nil || p.Prompt != "" {
			return errors.New("prompt.WithPrompt: cannot set prompt more than once")
		}
		p.Prompt = promptText

		return nil
	}
}

// WithPromptFn sets the result of the callback function as the user message on the prompt.
func WithPromptFn(promptFn PromptFn) PromptOption {
	return func(p *Prompt) error {
		if p.PromptFn != nil || p.Prompt != "" {
			return errors.New("prompt.WithPromptFn: cannot set prompt more than once")
		}
		p.PromptFn = promptFn

		return nil
	}
}

// WithDefaultMessages adds messages to the prompt.
func WithDefaultMessages(msgs []*ai.Message) PromptOption {
	return func(p *Prompt) error {
		if p.MessagesFn != nil || len(p.Messages) > 0 {
			return errors.New("prompt.WithDefaultMessages: cannot set messages more than once")
		}
		p.Messages = msgs

		return nil
	}
}

// WithDefaultMessagesFn sets the result of the callback function as messages on the prompt.
func WithDefaultMessagesFn(msgsFn MessagesFn) PromptOption {
	return func(p *Prompt) error {
		if p.MessagesFn != nil || len(p.Messages) > 0 {
			return errors.New("prompt.WithDefaultMessages: cannot set messages more than once")
		}
		p.MessagesFn = msgsFn

		return nil
	}
}

// WithTools adds tools to the prompt.
func WithTools(tools ...ai.Tool) PromptOption {
	return func(p *Prompt) error {
		if p.Config.Tools != nil {
			return errors.New("prompt.WithTools: cannot set Tools more than once")
		}

		var toolSlice []ai.Tool
		toolSlice = append(toolSlice, tools...)
		p.Tools = toolSlice
		return nil
	}
}

// WithDefaultConfig adds default model configuration.
func WithDefaultConfig(config *ai.GenerationCommonConfig) PromptOption {
	return func(p *Prompt) error {
		if p.Config.GenerationConfig != nil {
			return errors.New("prompt.WithDefaultConfig: cannot set Config more than once")
		}
		p.Config.GenerationConfig = config
		return nil
	}
}

// WithInputType uses the type provided to derive the input schema.
// If passing eg. a struct with values, the struct definition will serve as the schema, the values will serve as defaults if no input is given at generation time.
func WithInputType(input any) PromptOption {
	return func(p *Prompt) error {
		if p.Config.InputSchema != nil {
			return errors.New("prompt.WithInputType: cannot set InputType more than once")
		}

		// Handle primitives, default to "value" as key
		// No default necessary, assumed type to be struct
		switch v := input.(type) {
		case int:
			input = map[string]any{"value": strconv.Itoa(v)}
		case float32:
		case float64:
			input = map[string]any{"value": fmt.Sprintf("%f", v)}
		case string:
			input = map[string]any{"value": v}
		// Pass map directly
		case map[string]any:
			input = v
		case bool:
			input = map[string]any{"value": strconv.FormatBool(v)}
		}

		p.Config.InputSchema = base.InferJSONSchema(input)

		// Set values as default input
		defaultInput := base.SchemaAsMap(p.Config.InputSchema)
		data, err := json.Marshal(input)
		if err != nil {
			return err
		}

		err = json.Unmarshal(data, &defaultInput)
		if err != nil {
			return err
		}

		p.Config.DefaultInput = defaultInput
		return nil
	}
}

// WithOutputType uses the type provided to derive the output schema.
func WithOutputType(output any) PromptOption {
	return func(p *Prompt) error {
		if p.Config.OutputSchema != nil {
			return errors.New("prompt.WithOutputType: cannot set OutputType more than once")
		}

		p.Config.OutputSchema = base.InferJSONSchema(output)
		p.Config.OutputFormat = ai.OutputFormatJSON

		return nil
	}
}

// WithOutputFormat adds the desired output format to the prompt.
func WithOutputFormat(format ai.OutputFormat) PromptOption {
	return func(p *Prompt) error {
		if p.Config.OutputFormat != "" && p.Config.OutputFormat != format {
			return errors.New("prompt.WithOutputFormat: OutputFormat does not match set OutputSchema")
		}
		if format == ai.OutputFormatJSON && p.Config.OutputSchema == nil {
			return errors.New("prompt.WithOutputFormat: to set OutputFormat to JSON, OutputSchema must be set")
		}

		p.Config.OutputFormat = format
		return nil
	}
}

// WithMetadata adds arbitrary metadata.
func WithMetadata(metadata map[string]any) PromptOption {
	return func(p *Prompt) error {
		if p.Config.Metadata != nil {
			return errors.New("prompt.WithMetadata: cannot set Metadata more than once")
		}
		p.Config.Metadata = metadata
		return nil
	}
}

// WithDefaultModel adds the default Model to use.
func WithDefaultModel(model ai.Model) PromptOption {
	return func(p *Prompt) error {
		if p.Config.ModelName != "" || p.Config.Model != nil {
			return errors.New("prompt.WithDefaultModel: config must specify exactly once, either ModelName or Model")
		}
		p.Config.Model = model
		return nil
	}
}

// WithDefaultModelName adds the name of the default Model to use.
func WithDefaultModelName(name string) PromptOption {
	return func(p *Prompt) error {
		if p.Config.ModelName != "" || p.Config.Model != nil {
			return errors.New("prompt.WithDefaultModelName: config must specify exactly once, either ModelName or Model")
		}
		p.Config.ModelName = name
		return nil
	}
}

// WithDefaultMaxTurns sets the default maximum number of tool call iterations for the prompt.
func WithDefaultMaxTurns(maxTurns int) PromptOption {
	return func(p *Prompt) error {
		if maxTurns <= 0 {
			return fmt.Errorf("maxTurns must be greater than 0, got %d", maxTurns)
		}
		if p.Config.MaxTurns != 0 {
			return errors.New("prompt.WithMaxTurns: cannot set MaxTurns more than once")
		}
		p.Config.MaxTurns = maxTurns
		return nil
	}
}

// WithDefaultReturnToolRequests configures whether by default to return tool requests instead of making the tool calls and continuing the generation.
func WithDefaultReturnToolRequests(returnToolRequests bool) PromptOption {
	return func(p *Prompt) error {
		if p.Config.ReturnToolRequests {
			return errors.New("prompt.WithReturnToolRequests: cannot set ReturnToolRequests more than once")
		}
		p.Config.ReturnToolRequests = returnToolRequests
		return nil
	}
}

// WithDefaultToolChoice configures whether by default tool calls are required, disabled, or optional for the prompt.
func WithDefaultToolChoice(toolChoice ai.ToolChoice) PromptOption {
	return func(p *Prompt) error {
		if p.Config.ToolChoice != "" {
			return errors.New("prompt.WithToolChoice: cannot set ToolChoice more than once")
		}
		p.Config.ToolChoice = toolChoice
		return nil
	}
}

func WithRender(renderFn RenderFn) PromptOption {
	return func(p *Prompt) error {
		if p.Config.RenderFn != nil {
			return errors.New("prompt.WithRender: cannot set WithRender more than once")
		}
		p.Config.RenderFn = renderFn
		return nil
	}
}
