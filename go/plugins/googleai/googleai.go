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

package googleai

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/google/generative-ai-go/genai"
	"google.golang.org/api/iterator"
	"google.golang.org/api/option"
)

func newClient(ctx context.Context, apiKey string) (*genai.Client, error) {
	return genai.NewClient(ctx, option.WithAPIKey(apiKey))
}

type generator struct {
	model  string
	client *genai.Client
	//session *genai.ChatSession // non-nil if we're in the middle of a chat
}

func (g *generator) Generate(ctx context.Context, input *ai.GenerateRequest, cb func(context.Context, *ai.Candidate) error) (*ai.GenerateResponse, error) {
	gm := g.client.GenerativeModel(g.model)

	// Translate from a ai.GenerateRequest to a genai request.
	gm.SetCandidateCount(int32(input.Candidates))
	if c, ok := input.Config.(*ai.GenerationCommonConfig); ok && c != nil {
		gm.SetMaxOutputTokens(int32(c.MaxOutputTokens))
		gm.StopSequences = c.StopSequences
		gm.SetTemperature(float32(c.Temperature))
		gm.SetTopK(int32(c.TopK))
		gm.SetTopP(float32(c.TopP))
	}

	// Start a "chat".
	cs := gm.StartChat()

	// All but the last message goes in the history field.
	messages := input.Messages
	for len(messages) > 1 {
		m := messages[0]
		messages = messages[1:]
		cs.History = append(cs.History, &genai.Content{
			Parts: convertParts(m.Content),
			Role:  string(m.Role),
		})
	}
	// The last message gets added to the parts slice.
	var parts []genai.Part
	if len(messages) > 0 {
		parts = convertParts(messages[0].Content)
	}

	// Convert input.Tools and append to gm.Tools
	for _, t := range input.Tools {
		schema := &genai.Schema{}
		schema.Type = genai.TypeObject
		schema.Properties = map[string]*genai.Schema{}
		for k, v := range t.InputSchema {
			typ := genai.TypeUnspecified
			switch v {
			case "string":
				typ = genai.TypeString
			case "float64":
				typ = genai.TypeNumber
			case "int":
				typ = genai.TypeInteger
			case "bool":
				typ = genai.TypeBoolean
			default:
				return nil, fmt.Errorf("schema value \"%s\" not allowed", v)
			}
			schema.Properties[k] = &genai.Schema{Type: typ}
		}
		fd := &genai.FunctionDeclaration{Name: t.Name, Parameters: schema}
		gm.Tools = append(gm.Tools, &genai.Tool{FunctionDeclarations: []*genai.FunctionDeclaration{fd}})
	}
	// TODO: gm.ToolConfig?

	// Send out the actual request.
	if cb == nil {
		resp, err := cs.SendMessage(ctx, parts...)
		if err != nil {
			return nil, err
		}
		r := translateResponse(resp)
		r.Request = input
		return r, nil
	}

	// Streaming version.
	iter := cs.SendMessageStream(ctx, parts...)
	var r *ai.GenerateResponse
	for {
		chunk, err := iter.Next()
		if err == iterator.Done {
			break
		}
		if err != nil {
			return nil, err
		}
		// Send candidates to the callback.
		for _, c := range chunk.Candidates {
			err := cb(ctx, translateCandidate(c))
			if err != nil {
				return nil, err
			}
		}
		if r == nil {
			// Save all other fields of first response
			// so we can surface them at the end.
			// TODO: necessary? Use last instead of first? merge somehow?
			chunk.Candidates = nil
			r = translateResponse(chunk)
		}
	}
	if r == nil {
		// No candidates were returned. Probably rare, but it might avoid a NPE
		// to return an empty instead of nil result.
		r = &ai.GenerateResponse{}
	}
	r.Request = input
	return r, nil
}

// translateCandidate translates from a genai.GenerateContentResponse to an ai.GenerateResponse.
func translateCandidate(cand *genai.Candidate) *ai.Candidate {
	c := &ai.Candidate{}
	c.Index = int(cand.Index)
	switch cand.FinishReason {
	case genai.FinishReasonStop:
		c.FinishReason = ai.FinishReasonStop
	case genai.FinishReasonMaxTokens:
		c.FinishReason = ai.FinishReasonLength
	case genai.FinishReasonSafety:
		c.FinishReason = ai.FinishReasonBlocked
	case genai.FinishReasonRecitation:
		c.FinishReason = ai.FinishReasonBlocked
	case genai.FinishReasonOther:
		c.FinishReason = ai.FinishReasonOther
	default: // Unspecified
		c.FinishReason = ai.FinishReasonUnknown
	}
	m := &ai.Message{}
	m.Role = ai.Role(cand.Content.Role)
	for _, part := range cand.Content.Parts {
		var p *ai.Part
		switch part := part.(type) {
		case genai.Text:
			p = ai.NewTextPart(string(part))
		case genai.Blob:
			p = ai.NewMediaPart(part.MIMEType, string(part.Data))
		case genai.FunctionCall:
			p = ai.NewToolRequestPart(&ai.ToolRequest{
				Name:  part.Name,
				Input: part.Args,
			})
		default:
			panic(fmt.Sprintf("unknown part %#v", part))
		}
		m.Content = append(m.Content, p)
	}
	c.Message = m
	return c
}

// Translate from a genai.GenerateContentResponse to a ai.GenerateResponse.
func translateResponse(resp *genai.GenerateContentResponse) *ai.GenerateResponse {
	r := &ai.GenerateResponse{}
	for _, c := range resp.Candidates {
		r.Candidates = append(r.Candidates, translateCandidate(c))
	}
	return r
}

// NewGenerator returns an [ai.Generator] which sends a request to
// the google AI model and returns the response.
func NewGenerator(ctx context.Context, model, apiKey string) (ai.Generator, error) {
	client, err := newClient(ctx, apiKey)
	if err != nil {
		return nil, err
	}
	return &generator{
		model:  model,
		client: client,
	}, nil
}

// Init registers all the actions in this package with [ai]'s Register calls.
func Init(ctx context.Context, model, apiKey string) error {
	e, err := NewEmbedder(ctx, model, apiKey)
	if err != nil {
		return err
	}
	ai.RegisterEmbedder("google-genai", e)
	g, err := NewGenerator(ctx, model, apiKey)
	if err != nil {
		return err
	}
	ai.RegisterGenerator("google-genai", model, &ai.GeneratorMetadata{
		Label: "Google AI - " + model,
		Supports: ai.GeneratorCapabilities{
			Multiturn: true,
		},
	}, g)

	return nil
}

// convertParts converts a slice of *ai.Part to a slice of genai.Part.
func convertParts(parts []*ai.Part) []genai.Part {
	res := make([]genai.Part, 0, len(parts))
	for _, p := range parts {
		res = append(res, convertPart(p))
	}
	return res
}

// convertPart converts a *ai.Part to a genai.Part.
func convertPart(p *ai.Part) genai.Part {
	switch {
	case p.IsText():
		return genai.Text(p.Text)
	case p.IsMedia():
		return genai.Blob{MIMEType: p.ContentType, Data: []byte(p.Text)}
	case p.IsData():
		panic("googleai does not support Data parts")
	case p.IsToolResponse():
		toolResp := p.ToolResponse
		return genai.FunctionResponse{
			Name:     toolResp.Name,
			Response: toolResp.Output,
		}
	case p.IsToolRequest():
		toolReq := p.ToolRequest
		return genai.FunctionCall{
			Name: toolReq.Name,
			Args: toolReq.Input,
		}
	default:
		panic("unknown part type in a request")
	}
}
