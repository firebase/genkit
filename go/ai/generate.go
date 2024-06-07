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
	"github.com/firebase/genkit/go/core/logger"
)

// A ModelAction is used to generate content from an AI model.
type ModelAction = core.Action[*GenerateRequest, *GenerateResponse, *Candidate]

// ModelStreamingCallback is the type for the streaming callback of a model.
type ModelStreamingCallback = func(context.Context, *Candidate) error

// ModelCapabilities describes various capabilities of the model.
type ModelCapabilities struct {
	Multiturn  bool // the model can handle multiple request-response interactions
	Media      bool // the model supports media as well as text input
	Tools      bool // the model supports tools
	SystemRole bool // the model supports a system prompt or role
}

// ModelMetadata is the metadata of the model, specifying things like nice user-visible label, capabilities, etc.
type ModelMetadata struct {
	Label    string
	Supports ModelCapabilities
}

// DefineModel registers the given generate function as an action, and returns a
// [ModelAction] that runs it.
func DefineModel(provider, name string, metadata *ModelMetadata, generate func(context.Context, *GenerateRequest, ModelStreamingCallback) (*GenerateResponse, error)) *ModelAction {
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
	return core.DefineStreamingAction(provider, name, core.ActionTypeModel, map[string]any{
		"model": metadataMap,
	}, generate)
}

// LookupModel looks up a [ModelAction] registered by [DefineModel].
// It returns nil if the model was not defined.
func LookupModel(provider, name string) *ModelAction {
	return core.LookupActionFor[*GenerateRequest, *GenerateResponse, *Candidate](core.ActionTypeModel, provider, name)
}

// Generate applies a [ModelAction] to some input, handling tool requests.
func Generate(ctx context.Context, g *ModelAction, req *GenerateRequest, cb ModelStreamingCallback) (*GenerateResponse, error) {
	if err := conformOutput(req); err != nil {
		return nil, err
	}

	for {
		resp, err := g.Run(ctx, req, cb)
		if err != nil {
			return nil, err
		}

		candidates, err := validCandidates(ctx, resp)
		if err != nil {
			return nil, err
		}
		resp.Candidates = candidates

		newReq, err := handleToolRequest(ctx, req, resp)
		if err != nil {
			return nil, err
		}
		if newReq == nil {
			return resp, nil
		}

		req = newReq
	}
}

// conformOutput appends a message to the request indicating conformance to the expected schema.
func conformOutput(req *GenerateRequest) error {
	if req.Output != nil && req.Output.Format == OutputFormatJSON && len(req.Messages) > 0 {
		jsonBytes, err := json.Marshal(req.Output.Schema)
		if err != nil {
			return fmt.Errorf("expected schema is not valid: %w", err)
		}

		escapedJSON := strconv.Quote(string(jsonBytes))
		part := NewTextPart(fmt.Sprintf("Output should be in JSON format and conform to the following schema:\n\n```%s```", escapedJSON))
		req.Messages[len(req.Messages)-1].Content = append(req.Messages[len(req.Messages)-1].Content, part)
	}
	return nil
}

// validCandidates finds all candidates that match the expected schema.
// It will strip JSON markdown delimiters from the response.
func validCandidates(ctx context.Context, resp *GenerateResponse) ([]*Candidate, error) {
	var candidates []*Candidate
	for i, c := range resp.Candidates {
		c, err := validCandidate(c, resp.Request.Output)
		if err == nil {
			candidates = append(candidates, c)
		} else {
			logger.FromContext(ctx).Debug("candidate did not match expected schema", "index", i, "error", err.Error())
		}
	}
	if len(candidates) == 0 {
		return nil, errors.New("generation resulted in no candidates matching expected schema")
	}
	return candidates, nil
}

// validCandidate will validate the candidate's response against the expected schema.
// It will return an error if it does not match, otherwise it will return a candidate with JSON content and type.
func validCandidate(c *Candidate, output *GenerateRequestOutput) (*Candidate, error) {
	if output != nil && output.Format == OutputFormatJSON {
		text, err := c.Text()
		if err != nil {
			return nil, err
		}
		text = stripJSONDelimiters(text)
		var schemaBytes []byte
		schemaBytes, err = json.Marshal(output.Schema)
		if err != nil {
			return nil, fmt.Errorf("expected schema is not valid: %w", err)
		}
		if err = core.ValidateRaw([]byte(text), schemaBytes); err != nil {
			return nil, err
		}
		// TODO: Verify that it okay to replace all content with JSON.
		c.Message.Content = []*Part{NewJSONPart(text)}
	}
	return c, nil
}

// stripJSONDelimiters strips Markdown JSON delimiters that may come back in the response.
func stripJSONDelimiters(s string) string {
	s = strings.TrimSpace(s)
	delimiters := []string{"```", "~~~"}
	for _, delimiter := range delimiters {
		if strings.HasPrefix(s, delimiter) && strings.HasSuffix(s, delimiter) {
			s = strings.TrimPrefix(s, delimiter)
			s = strings.TrimSuffix(s, delimiter)
			s = strings.TrimSpace(s)
			if strings.HasPrefix(s, "json") {
				s = strings.TrimPrefix(s, "json")
				s = strings.TrimSpace(s)
			}
			break
		}
	}
	return s
}

// handleToolRequest checks if a tool was requested by a model.
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

	toolReq := part.ToolRequest
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
		return "", errors.New("candidate has no message")
	}
	if len(msg.Content) == 0 {
		return "", errors.New("candidate message has no content")
	}
	if len(msg.Content) == 1 {
		return msg.Content[0].Text, nil
	} else {
		var sb strings.Builder
		for _, p := range msg.Content {
			sb.WriteString(p.Text)
		}
		return sb.String(), nil
	}
}
