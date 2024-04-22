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

	"github.com/aymerick/raymond"
	"github.com/google/genkit/go/ai"
	"github.com/invopop/jsonschema"
	"gopkg.in/yaml.v3"
)

// promptDirectory is the directory where dotprompt files are found.
var promptDirectory string

// SetDirectory sets the directory where dotprompt files are read from.
func SetDirectory(directory string) {
	promptDirectory = directory
}

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
	// The name of the prompt variant, if any.
	// Variants can be used for easy testing of a tweaked prompt.
	Variant string

	// A hash of the prompt contents.
	Hash string

	// The template for the prompt.
	Template *raymond.Template

	// The prompt YAML frontmatter.
	Frontmatter *Frontmatter
}

// Open opens and parses a dotprompt file.
// The name is a base file name, without the ".prompt" extension.
func Open(name string) (*Prompt, error) {
	return OpenVariant(name, "")
}

// OpenVariant opens a parses a dotprompt file with a variant.
// If the variant does not exist, the non-variant version is tried.
func OpenVariant(name, variant string) (*Prompt, error) {
	if promptDirectory == "" {
		// The TypeScript code defaults to ./prompts,
		// but that makes the program change behavior
		// depending on where it is run.
		return nil, errors.New("missing call to dotprompt.SetDirectory")
	}

	vname := name
	if variant != "" {
		vname = name + "." + variant
	}

	fileName := filepath.Join(promptDirectory, vname+".prompt")

	data, err := os.ReadFile(fileName)
	if err != nil {
		if variant != "" && errors.Is(err, fs.ErrNotExist) {
			slog.Warn("prompt not found, trying without variant", "name", name, "variant", variant)
			return OpenVariant(name, "")
		}

		return nil, fmt.Errorf("failed to read dotprompt file %q: %w", name, err)
	}

	return Parse(name, variant, data)
}

// Frontmatter is the data we may see, YAML encoded, at the
// start of a dotprompt file. It appears within --- lines.
// These fields are optional.
type Frontmatter struct {
	// The name of the prompt.
	Name string
	// The prompt variant.
	Variant string
	// The name of the model for which the prompt is input.
	Model string

	// TODO(iant): document
	Tools []*ai.ToolDefinition

	// Number of candidates to generate when passing the prompt
	// to a generator. If 0, uses 1.
	Candidates int

	// Details for the model.
	Config *ai.GenerationConfig

	// Description of input data.
	Input struct {
		Schema  *jsonschema.Schema
		Default map[string]any
	}

	// Desired output format.
	Output *ai.GenerateRequestOutput

	// Arbitrary metadata.
	Metadata map[string]any
}

// frontmatterYAML is the type we use to unpack the frontmatter.
// We do it this way so that we can handle the input and output
// fields as picoschema, while returning them as jsonschema.Schema.
type frontmatterYAML struct {
	Name       string               `yaml:"name,omitempty"`
	Variant    string               `yaml:"variant,omitempty"`
	Model      string               `yaml:"model,omitempty"`
	Tools      []*ai.ToolDefinition `yaml:"tools,omitempty"`
	Candidates int                  `yaml:"candidates,omitempty"`
	Config     *ai.GenerationConfig `yaml:"config,omitempty"`
	Input      struct {
		Schema  any            `yaml:"schema,omitempty"`
		Default map[string]any `yaml:"default,omitempty"`
	} `yaml:"input,omitempty"`
	Output struct {
		Format string `yaml:"format,omitempty"`
		Schema any    `yaml:"schema,omitempty"`
	} `yaml:"output,omitempty"`
	Metadata map[string]any `yaml:"metadata,omitempty"`
}

// parse parses the contents of a dotprompt file.
func Parse(name, variant string, data []byte) (*Prompt, error) {
	const header = "---\n"
	var front *Frontmatter
	if bytes.HasPrefix(data, []byte(header)) {
		var err error
		front, data, err = parseFrontmatter(data[len(header):])
		if err != nil {
			return nil, err
		}
	}

	template, err := raymond.Parse(string(data))
	if err != nil {
		return nil, fmt.Errorf("failed to parse template: %w", err)
	}
	template.RegisterHelpers(templateHelpers)

	prompt := &Prompt{
		Name:        name,
		Variant:     variant,
		Hash:        fmt.Sprintf("%02x", sha256.Sum256(data)),
		Template:    template,
		Frontmatter: front,
	}
	return prompt, nil
}

// parseFrontmatter parses the initial YAML frontmatter of a dotprompt file.
// Along with the frontmatter itself, it returns the remaining data.
func parseFrontmatter(data []byte) (*Frontmatter, []byte, error) {
	const footer = "\n---\n"
	end := bytes.Index(data, []byte(footer))
	if end == -1 {
		return nil, nil, errors.New("dotprompt: missing marker for end of frontmatter")
	}
	input := data[:end]
	var fy frontmatterYAML
	if err := yaml.Unmarshal(input, &fy); err != nil {
		return nil, nil, fmt.Errorf("dotprompt: failed to parse YAML frontmatter: %w", err)
	}

	ret := &Frontmatter{
		Name:       fy.Name,
		Variant:    fy.Variant,
		Model:      fy.Model,
		Tools:      fy.Tools,
		Candidates: fy.Candidates,
		Config:     fy.Config,
		Metadata:   fy.Metadata,
	}

	inputSchema, err := picoschemaToJSONSchema(fy.Input.Schema)
	if err != nil {
		return nil, nil, fmt.Errorf("dotprompt: can't parse input: %w", err)
	}
	ret.Input.Schema = inputSchema
	ret.Input.Default = fy.Input.Default

	outputSchema, err := picoschemaToJSONSchema(fy.Output.Schema)
	if err != nil {
		return nil, nil, fmt.Errorf("dotprompt: can't parse output: %w", err)
	}

	var generateOutputSchema map[string]any
	if outputSchema != nil {
		// We have a jsonschema.Schema and we want a map[string]any.
		// TODO(iant): This conversion is useless.

		// Sort so that testing is reliable.
		// This is not required if not testing.
		sortSchemaSlices(outputSchema)

		data, err := json.Marshal(outputSchema)
		if err != nil {
			return nil, nil, fmt.Errorf("dotprompt: can't JSON marshal JSON schema: %w", err)
		}
		if err := json.Unmarshal(data, &generateOutputSchema); err != nil {
			return nil, nil, fmt.Errorf("dotprompt: can't unmarshal JSON schema: %w", err)
		}
	}

	// TODO(iant): The TypeScript codes supports media also,
	// but there is no ai.OutputFormatMedia.
	var of ai.OutputFormat
	switch fy.Output.Format {
	case "":
	case string(ai.OutputFormatJSON):
		of = ai.OutputFormatJSON
	case string(ai.OutputFormatText):
		of = ai.OutputFormatText
	default:
		return nil, nil, fmt.Errorf("dotprompt: unrecognized output format %q", fy.Output.Format)
	}

	if of != "" || generateOutputSchema != nil {
		ret.Output = &ai.GenerateRequestOutput{
			Format: of,
			Schema: generateOutputSchema,
		}
	}

	return ret, data[end+len(footer):], nil
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
