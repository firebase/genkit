// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Package dotprompt parses and renders dotprompt files.
package dotprompt

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"log/slog"
	"os"
	"path/filepath"
	"slices"
	"strconv"

	"github.com/aymerick/raymond"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/invopop/jsonschema"
	"gopkg.in/yaml.v3"
)

// Prompt is a parsed dotprompt file.
//
// A dotprompt file consists of YAML frontmatter within --- lines,
// followed by a template written in the [Handlebars] language.
//
// The YAML frontmatter will normally define a JSON schema
// describing the expected input and output variables.
// The input variables will appear in the template.
// The JSON schemas may be defined in a compact picoschema format.
//
// The templates are evaluated with a couple of helpers.
//   - {{role r}} changes to a new role for the following text
//   - {{media url=URL}} adds a URL with an optional contentType
//
// [Handlebars]: https://handlebarsjs.com
type Prompt struct {
	// The name of the prompt. Optional unless the prompt is
	// registered as an action.
	Name string
	Config
	// The parsed prompt template.
	Template *raymond.Template
	// The original prompt template text.
	TemplateText string
	// A hash of the prompt contents.
	hash string
	// A prompt that renders the prompt.
	prompt *ai.Prompt
}

// Config is optional configuration for a [Prompt].
type Config struct {
	// The prompt variant.
	Variant string
	// The name of the model for which the prompt is input.
	// If this is non-empty, Model should be nil.
	ModelName string
	// The Model to use.
	// If this is set, ModelName should be an empty string.
	Model ai.Model
	// TODO: document
	Tools []ai.Tool
	// Details for the model.
	GenerationConfig *ai.GenerationCommonConfig
	// Schema for input variables.
	InputSchema *jsonschema.Schema
	// Default input variable values
	DefaultInput map[string]any
	// Desired output format.
	OutputFormat ai.OutputFormat
	// Desired output schema, for JSON output.
	OutputSchema *jsonschema.Schema
	// Arbitrary metadata.
	Metadata map[string]any
	// ToolChoice is the tool choice to use.
	ToolChoice ai.ToolChoice
	// MaxTurns is the maximum number of turns.
	MaxTurns int
	// ReturnToolRequests is whether to return tool requests.
	ReturnToolRequests bool
}

// PromptOption configures params for the prompt
type PromptOption func(p *Prompt) error

// Open opens and parses a dotprompt file.
// The name is a base file name, without the ".prompt" extension.
func Open(g *genkit.Genkit, name string) (*Prompt, error) {
	return OpenVariant(g, name, "")
}

// OpenVariant opens a parses a dotprompt file with a variant.
// If the variant does not exist, the non-variant version is tried.
func OpenVariant(g *genkit.Genkit, name, variant string) (*Prompt, error) {
	if g.Params.PromptDir == "" {
		// The TypeScript code defaults to ./prompts,
		// but that makes the program change behavior
		// depending on where it is run.
		return nil, errors.New("PromptDir in Genkit options is empty")
	}

	vname := name
	if variant != "" {
		vname = name + "." + variant
	}

	fileName := filepath.Join(g.Params.PromptDir, vname+".prompt")

	data, err := os.ReadFile(fileName)
	if err != nil {
		if variant != "" && errors.Is(err, fs.ErrNotExist) {
			slog.Warn("prompt not found, trying without variant", "name", name, "variant", variant)
			return OpenVariant(g, name, "")
		}

		return nil, fmt.Errorf("failed to read dotprompt file %q: %w", name, err)
	}

	return Parse(g, name, variant, data)
}

// frontmatterYAML is the type we use to unpack the frontmatter.
// (Frontmatter is the data we may see, YAML encoded, at the
// start of a dotprompt file. It appears within --- lines.)
// We do it this way so that we can handle the input and output
// fields as picoschema, while returning them as jsonschema.Schema.
type frontmatterYAML struct {
	Name       string                     `yaml:"name,omitempty"`
	Variant    string                     `yaml:"variant,omitempty"`
	Model      string                     `yaml:"model,omitempty"`
	Tools      []string                   `yaml:"tools,omitempty"`
	Candidates int                        `yaml:"candidates,omitempty"`
	Config     *ai.GenerationCommonConfig `yaml:"config,omitempty"`
	Input      struct {
		Schema  any            `yaml:"schema,omitempty"`
		Default map[string]any `yaml:"default,omitempty"`
	} `yaml:"input,omitempty"`
	Output struct {
		Format string `yaml:"format,omitempty"`
		Schema any    `yaml:"schema,omitempty"`
	} `yaml:"output,omitempty"`
	Metadata           map[string]any `yaml:"metadata,omitempty"`
	ToolChoice         string         `yaml:"toolChoice,omitempty"`
	MaxTurns           int            `yaml:"maxTurns,omitempty"`
	ReturnToolRequests bool           `yaml:"returnToolRequests,omitempty"`
}

// Parse parses the contents of a dotprompt file.
func Parse(g *genkit.Genkit, name, variant string, data []byte) (*Prompt, error) {
	const header = "---\n"
	var fmName string
	var cfg Config
	if bytes.HasPrefix(data, []byte(header)) {
		var err error
		fmName, cfg, data, err = parseFrontmatter(g, data[len(header):])
		if err != nil {
			return nil, err
		}
	}
	// The name argument takes precedence over the name in the frontmatter.
	if name == "" {
		name = fmName
	}

	return newPrompt(name, string(data), fmt.Sprintf("%02x", sha256.Sum256(data)), cfg)
}

// newPrompt creates a new prompt.
// templateText should be a handlebars template.
// hash is its SHA256 hash as a hex string.
func newPrompt(name, templateText, hash string, config Config) (*Prompt, error) {
	template, err := raymond.Parse(templateText)
	if err != nil {
		return nil, fmt.Errorf("failed to parse template: %w", err)
	}
	template.RegisterHelpers(templateHelpers)
	return &Prompt{
		Name:         name,
		Config:       config,
		hash:         hash,
		Template:     template,
		TemplateText: templateText,
	}, nil
}

// parseFrontmatter parses the initial YAML frontmatter of a dotprompt file.
// It returns the frontmatter as a Config along with the remaining data.
func parseFrontmatter(g *genkit.Genkit, data []byte) (name string, c Config, rest []byte, err error) {
	const footer = "\n---\n"
	end := bytes.Index(data, []byte(footer))
	if end == -1 {
		return "", Config{}, nil, errors.New("dotprompt: missing marker for end of frontmatter")
	}
	input := data[:end]
	var fy frontmatterYAML
	if err := yaml.Unmarshal(input, &fy); err != nil {
		return "", Config{}, nil, fmt.Errorf("dotprompt: failed to parse YAML frontmatter: %w", err)
	}

	var tools []ai.Tool
	for _, tn := range fy.Tools {
		tools = append(tools, genkit.LookupTool(g, tn))
	}

	ret := Config{
		Variant:            fy.Variant,
		ModelName:          fy.Model,
		Tools:              tools,
		GenerationConfig:   fy.Config,
		DefaultInput:       fy.Input.Default,
		Metadata:           fy.Metadata,
		ToolChoice:         ai.ToolChoice(fy.ToolChoice),
		MaxTurns:           fy.MaxTurns,
		ReturnToolRequests: fy.ReturnToolRequests,
	}

	inputSchema, err := picoschemaToJSONSchema(fy.Input.Schema)
	if err != nil {
		return "", Config{}, nil, fmt.Errorf("dotprompt: can't parse input: %w", err)
	}
	ret.InputSchema = inputSchema

	outputSchema, err := picoschemaToJSONSchema(fy.Output.Schema)
	if err != nil {
		return "", Config{}, nil, fmt.Errorf("dotprompt: can't parse output: %w", err)
	}

	if outputSchema != nil {
		// We have a jsonschema.Schema and we want a map[string]any.
		// TODO: This conversion is useless.

		// Sort so that testing is reliable.
		// This is not required if not testing.
		sortSchemaSlices(outputSchema)

		data, err := json.Marshal(outputSchema)
		if err != nil {
			return "", Config{}, nil, fmt.Errorf("dotprompt: can't JSON marshal JSON schema: %w", err)
		}
		if err := json.Unmarshal(data, &ret.OutputSchema); err != nil {
			return "", Config{}, nil, fmt.Errorf("dotprompt: can't unmarshal JSON schema: %w", err)
		}
	}

	// TODO: The TypeScript codes supports media also,
	// but there is no ai.OutputFormatMedia.
	switch fy.Output.Format {
	case "":
	case string(ai.OutputFormatJSON):
		ret.OutputFormat = ai.OutputFormatJSON
	case string(ai.OutputFormatText):
		ret.OutputFormat = ai.OutputFormatText
	default:
		return "", Config{}, nil, fmt.Errorf("dotprompt: unrecognized output format %q", fy.Output.Format)
	}
	return fy.Name, ret, data[end+len(footer):], nil
}

// Define creates and registers a new Prompt. This can be called from code that
// doesn't have a prompt file.
func Define(g *genkit.Genkit, name, templateText string, opts ...PromptOption) (*Prompt, error) {
	p, err := New(name, templateText, Config{})
	if err != nil {
		return nil, err
	}

	for _, with := range opts {
		err := with(p)
		if err != nil {
			return nil, err
		}
	}

	// fallback to default model name if no model was specified
	if p.Config.ModelName == "" && p.Config.Model == nil {
		p.Config.ModelName = g.Params.DefaultModel
	}

	p.Register(g)
	return p, nil
}

// New creates a new Prompt without registering it.
// This may be used for testing or for direct calls not using the
// genkit action and flow mechanisms.
func New(name, templateText string, cfg Config) (*Prompt, error) {
	hash := fmt.Sprintf("%02x", sha256.Sum256([]byte(templateText)))
	return newPrompt(name, templateText, hash, cfg)
}

// sortSchemaSlices sorts the slices in a jsonschema to permit
// consistent comparisons. We only bother with the fields we need
// for the tests we have.
func sortSchemaSlices(s *jsonschema.Schema) {
	slices.Sort(s.Required)
	if s.Properties != nil {
		for p := s.Properties.Oldest(); p != nil; p = p.Next() {
			sortSchemaSlices(p.Value)
		}
	}
	if s.Items != nil {
		sortSchemaSlices(s.Items)
	}
}

// WithTools adds tools to the prompt.
func WithTools(tools ...ai.Tool) PromptOption {
	return func(p *Prompt) error {
		if p.Config.Tools != nil {
			return errors.New("dotprompt.WithTools: cannot set Tools more than once")
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
			return errors.New("dotprompt.WithDefaultConfig: cannot set Config more than once")
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
			return errors.New("dotprompt.WithInputType: cannot set InputType more than once")
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
		}

		p.Config.InputSchema = base.InferJSONSchemaNonReferencing(input)

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
			return errors.New("dotprompt.WithOutputType: cannot set OutputType more than once")
		}

		p.Config.OutputSchema = base.InferJSONSchemaNonReferencing(output)
		p.Config.OutputFormat = ai.OutputFormatJSON

		return nil
	}
}

// WithOutputFormat adds the desired output format to the prompt
func WithOutputFormat(format ai.OutputFormat) PromptOption {
	return func(p *Prompt) error {
		if p.Config.OutputFormat != "" && p.Config.OutputFormat != format {
			return errors.New("dotprompt.WithOutputFormat: OutputFormat does not match set OutputSchema")
		}
		if format == ai.OutputFormatJSON && p.Config.OutputSchema == nil {
			return errors.New("dotprompt.WithOutputFormat: to set OutputFormat to JSON, OutputSchema must be set")
		}

		p.Config.OutputFormat = format
		return nil
	}
}

// WithMetadata adds arbitrary metadata.
func WithMetadata(metadata map[string]any) PromptOption {
	return func(p *Prompt) error {
		if p.Config.Metadata != nil {
			return errors.New("dotprompt.WithMetadata: cannot set Metadata more than once")
		}
		p.Config.Metadata = metadata
		return nil
	}
}

// WithDefaultModel adds the default Model to use.
func WithDefaultModel(model ai.Model) PromptOption {
	return func(p *Prompt) error {
		if p.Config.ModelName != "" || p.Config.Model != nil {
			return errors.New("dotprompt.WithDefaultModel: config must specify exactly once, either ModelName or Model")
		}
		p.Config.Model = model
		return nil
	}
}

// WithDefaultModelName adds the name of the default Model to use.
func WithDefaultModelName(name string) PromptOption {
	return func(p *Prompt) error {
		if p.Config.ModelName != "" || p.Config.Model != nil {
			return errors.New("dotprompt.WithDefaultModelName: config must specify exactly once, either ModelName or Model")
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
			return errors.New("dotprompt.WithMaxTurns: cannot set MaxTurns more than once")
		}
		p.Config.MaxTurns = maxTurns
		return nil
	}
}

// WithDefaultReturnToolRequests configures whether by default to return tool requests instead of making the tool calls and continuing the generation.
func WithDefaultReturnToolRequests(returnToolRequests bool) PromptOption {
	return func(p *Prompt) error {
		if p.Config.ReturnToolRequests {
			return errors.New("dotprompt.WithReturnToolRequests: cannot set ReturnToolRequests more than once")
		}
		p.Config.ReturnToolRequests = returnToolRequests
		return nil
	}
}

// WithDefaultToolChoice configures whether by default tool calls are required, disabled, or optional for the prompt.
func WithDefaultToolChoice(toolChoice ai.ToolChoice) PromptOption {
	return func(p *Prompt) error {
		if p.Config.ToolChoice != "" {
			return errors.New("dotprompt.WithToolChoice: cannot set ToolChoice more than once")
		}
		p.Config.ToolChoice = toolChoice
		return nil
	}
}
