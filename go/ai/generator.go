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

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"slices"
	"strconv"
	"strings"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal"
	"github.com/xeipuuv/gojsonschema"
)

// Generator is the interface used to query an AI model.
type Generator interface {
	// If the streaming callback is non-nil:
	// - Each response candidate will be passed to that callback instead of
	//   populating the result's Candidates field.
	// - If the streaming callback returns a non-nil error, generation will stop
	//   and Generate immediately returns that error (and a nil response).
	Generate(context.Context, *GenerateRequest, func(context.Context, *Candidate) error) (*GenerateResponse, error)
}

// GeneratorCapabilities describes various capabilities of the generator.
type GeneratorCapabilities struct {
	Multiturn  bool
	Media      bool
	Tools      bool
	SystemRole bool
}

// GeneratorMetadata is the metadata of the generator, specifying things like nice user visible label, capabilities, etc.
type GeneratorMetadata struct {
	Label    string
	Supports GeneratorCapabilities
}

// RegisterGenerator registers the generator in the global registry.
func RegisterGenerator(provider, name string, metadata *GeneratorMetadata, generator Generator) {
	metadataMap := map[string]any{}
	if metadata != nil {
		if metadata.Label != "" {
			metadataMap["label"] = metadata.Label
		}
		supports := map[string]bool{
			"media":      metadata.Supports.Media,
			"multiturn":  metadata.Supports.Multiturn,
			"systemRole": metadata.Supports.SystemRole,
			"tools":      metadata.Supports.Tools,
		}
		metadataMap["supports"] = supports
	}
	core.RegisterAction(provider,
		core.NewStreamingAction(name, core.ActionTypeModel, map[string]any{
			"model": metadataMap,
		}, generator.Generate))
}

// Generate applies a [Generator] to some input, handling tool requests.
func Generate(ctx context.Context, g Generator, input *GenerateRequest, cb func(context.Context, *Candidate) error) (*GenerateResponse, error) {
	if err := conformOutput(input); err != nil {
		return nil, err
	}

	for {
		resp, err := g.Generate(ctx, input, cb)
		if err != nil {
			return nil, err
		}

		candidates := findValidCandidates(ctx, resp)
		if len(candidates) == 0 {
			return nil, errors.New("generation resulted in no candidates matching provided output schema")
		}
		resp.Candidates = candidates

		newReq, err := handleToolRequest(ctx, input, resp)
		if err != nil {
			return nil, err
		}
		if newReq == nil {
			return resp, nil
		}

		input = newReq
	}
}

// generatorActionType is the instantiated core.Action type registered
// by RegisterGenerator.
type generatorActionType = core.Action[*GenerateRequest, *GenerateResponse, *Candidate]

// LookupGeneratorAction looks up an action registered by [RegisterGenerator]
// and returns a generator that invokes the action.
func LookupGeneratorAction(provider, name string) (Generator, error) {
	action := core.LookupAction(core.ActionTypeModel, provider, name)
	if action == nil {
		return nil, fmt.Errorf("LookupGeneratorAction: no generator action named %q/%q", provider, name)
	}
	actionInst, ok := action.(*generatorActionType)
	if !ok {
		return nil, fmt.Errorf("LookupGeneratorAction: generator action %q has type %T, want %T", name, action, &generatorActionType{})
	}
	return &generatorAction{actionInst}, nil
}

// generatorAction implements Generator by invoking an action.
type generatorAction struct {
	action *generatorActionType
}

// Generate implements Generator. This is like the [Generate] function,
// but invokes the [core.Action] rather than invoking the Generator
// directly.
func (ga *generatorAction) Generate(ctx context.Context, input *GenerateRequest, cb func(context.Context, *Candidate) error) (*GenerateResponse, error) {
	if err := conformOutput(input); err != nil {
		return nil, err
	}

	for {
		resp, err := ga.action.Run(ctx, input, cb)
		if err != nil {
			return nil, err
		}

		candidates := findValidCandidates(ctx, resp)
		if len(candidates) == 0 {
			return nil, errors.New("generation resulted in no candidates matching provided output schema")
		}
		resp.Candidates = candidates

		newReq, err := handleToolRequest(ctx, input, resp)
		if err != nil {
			return nil, err
		}
		if newReq == nil {
			return resp, nil
		}

		input = newReq
	}
}

// conformOutput appends a message to the request indicating conformance to the expected schema.
func conformOutput(input *GenerateRequest) error {
	if len(input.Output.Schema) > 0 && len(input.Messages) > 0 {
		jsonBytes, err := json.Marshal(input.Output.Schema)
		if err != nil {
			return fmt.Errorf("expected schema is not valid: %w", err)
		}

		jsonStr := string(jsonBytes)
		escapedJSON := strconv.Quote(jsonStr)
		part := &Part{
			text: fmt.Sprintf("Output should be in JSON format and conform to the following schema:\n\n```%s```", escapedJSON),
		}
		input.Messages[len(input.Messages)-1].Content = append(input.Messages[len(input.Messages)-1].Content, part)
	}
	return nil
}

// findValidCandidates finds all candidates that match the expected schema.
func findValidCandidates(ctx context.Context, resp *GenerateResponse) []*Candidate {
	candidates := []*Candidate{}
	for i, c := range resp.Candidates {
		err := validateCandidate(c, resp.Request.Output)
		if err == nil {
			candidates = append(candidates, c)
		} else {
			internal.Logger(ctx).Debug("candidate did not match provided output schema", "index", i, "error", err.Error())
		}
	}
	return candidates
}

// validateCandidate will check a candidate against the expected schema.
// It will return an error if it does not match, otherwise it will return nil.
func validateCandidate(candidate *Candidate, outputSchema *GenerateRequestOutput) error {
	if outputSchema.Format != OutputFormatJSON {
		return nil
	}

	text, err := candidate.Text()
	if err != nil {
		return err
	}

	text = stripJsonDelimiters(text)

	var jsonData interface{}
	err = json.Unmarshal([]byte(text), &jsonData)
	if err != nil {
		return fmt.Errorf("candidate did not have valid JSON: %w", err)
	}

	schemaBytes, err := json.Marshal(outputSchema.Schema)
	if err != nil {
		return fmt.Errorf("expected schema is not valid: %w", err)
	}

	schemaLoader := gojsonschema.NewStringLoader(string(schemaBytes))
	jsonLoader := gojsonschema.NewGoLoader(jsonData)
	result, err := gojsonschema.Validate(schemaLoader, jsonLoader)
	if err != nil {
		return fmt.Errorf("failed to validate expected schema: %w", err)
	}

	if !result.Valid() {
		var errMsg string
		for _, err := range result.Errors() {
			errMsg += fmt.Sprintf("- %s\n", err)
		}
		return fmt.Errorf("candidate did not match expected schema:\n%s", errMsg)
	}

	return nil
}

// stripJsonDelimiters strips JSON delimiters that may come back in the response.
func stripJsonDelimiters(s string) string {
	return strings.TrimSuffix(strings.TrimPrefix(s, "```json"), "```")
}

// handleToolRequest checks if a tool was requested by a generator.
// If a tool was requested, this runs the tool and returns an
// updated GenerateRequest. If no tool was requested this returns nil.
func handleToolRequest(ctx context.Context, req *GenerateRequest, resp *GenerateResponse) (*GenerateRequest, error) {
	if len(resp.Candidates) == 0 {
		return nil, nil
	}
	msg := resp.Candidates[0].Message
	if msg == nil || len(msg.Content) == 0 {
		return nil, nil
	}
	part := msg.Content[0]
	if !part.IsToolRequest() {
		return nil, nil
	}

	toolReq := part.ToolRequest()
	output, err := RunTool(ctx, toolReq.Name, toolReq.Input)
	if err != nil {
		return nil, err
	}

	toolResp := &Message{
		Content: []*Part{
			NewToolResponsePart(&ToolResponse{
				Name:   toolReq.Name,
				Output: output,
			}),
		},
		Role: RoleTool,
	}

	// Copy the GenerateRequest rather than modifying it.
	rreq := *req
	rreq.Messages = append(slices.Clip(rreq.Messages), msg, toolResp)

	return &rreq, nil
}

// Text returns the contents of the first candidate in a
// [GenerateResponse] as a string. It returns an error if there
// are no candidates or if the candidate has no message.
func (gr *GenerateResponse) Text() (string, error) {
	if len(gr.Candidates) == 0 {
		return "", errors.New("no candidates returned")
	}
	return gr.Candidates[0].Text()
}

// Text returns the contents of a [Candidate] as a string. It
// returns an error if the candidate has no message.
func (c *Candidate) Text() (string, error) {
	msg := c.Message
	if msg == nil {
		return "", errors.New("candidate with no message")
	}
	if len(msg.Content) == 0 {
		return "", errors.New("candidate message has no content")
	}
	if len(msg.Content) == 1 {
		return msg.Content[0].Text(), nil
	} else {
		var sb strings.Builder
		for _, p := range msg.Content {
			sb.WriteString(p.Text())
		}
		return sb.String(), nil
	}
}
