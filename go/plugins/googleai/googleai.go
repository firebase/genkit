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

	"github.com/google/generative-ai-go/genai"
	"github.com/google/genkit/go/ai"
	"github.com/google/genkit/go/genkit"
	"google.golang.org/api/iterator"
	"google.golang.org/api/option"
)

type embedder struct {
	model  string
	client *genai.Client
}

func (e *embedder) Embed(ctx context.Context, input *ai.EmbedRequest) ([]float32, error) {
	em := e.client.EmbeddingModel(e.model)
	parts := convertParts(input.Document.Content)
	res, err := em.EmbedContent(ctx, parts...)
	if err != nil {
		return nil, err
	}
	return res.Embedding.Values, nil
}

func newClient(ctx context.Context, apiKey string) (*genai.Client, error) {
	return genai.NewClient(ctx, option.WithAPIKey(apiKey))
}

// NewEmbedder returns an embedder which can compute the embedding
// of an input document given the Google AI model.
func NewEmbedder(ctx context.Context, model, apiKey string) (ai.Embedder, error) {
	client, err := newClient(ctx, apiKey)
	if err != nil {
		return nil, err
	}
	return &embedder{
		model:  model,
		client: client,
	}, nil
}

type generator struct {
	model  string
	client *genai.Client
}

func (g *generator) Generate(ctx context.Context, input *ai.GenerateRequest, cb genkit.StreamingCallback[*ai.Candidate]) (*ai.GenerateResponse, error) {
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
	//TODO: convert input.Tools and append to gm.Tools

	// Send out the actual request.
	if cb == nil {
		resp, err := cs.SendMessage(ctx, parts...)
		if err != nil {
			return nil, err
		}
		return translateResponse(resp), nil
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
	return r, nil
}

// translateCandidate Translate from a genai.GenerateContentResponse to a ai.GenerateResponse.
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
			p = ai.NewBlobPart(part.MIMEType, string(part.Data))
		case genai.FunctionResponse:
			p = ai.NewBlobPart("TODO", string(part.Name))
		default:
			panic("unknown part type")
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

// NewGenerator returns an action which sends a request to
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

// Init registers all the actions in this package with ai.
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
	ai.RegisterGenerator("google-genai", g)

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
	case p.IsPlainText():
		return genai.Text(p.Text())
	default:
		return genai.Blob{MIMEType: p.ContentType(), Data: []byte(p.Text())}
	}
}
