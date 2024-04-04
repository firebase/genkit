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

	"github.com/FirebasePrivate/genkit/go/genkit"
	"github.com/google/generative-ai-go/genai"
	"google.golang.org/api/option"
)

func embed(ctx context.Context, client *genai.Client, model string, input []genai.Part) ([]float32, error) {
	em := client.EmbeddingModel(model)
	res, err := em.EmbedContent(ctx, input...)
	if err != nil {
		return nil, err
	}
	return res.Embedding.Values, nil
}

func newClient(ctx context.Context, apiKey string) (*genai.Client, error) {
	return genai.NewClient(ctx, option.WithAPIKey(apiKey))
}

// NewTextEmbedder returns an action which computes the embedding of
// the input string in the given google AI model.
func NewTextEmbedder(ctx context.Context, model, apiKey string) (*genkit.Action[string, []float32], error) {
	client, err := newClient(ctx, apiKey)
	if err != nil {
		return nil, err
	}
	return genkit.NewAction(
		model,
		func(ctx context.Context, input string) ([]float32, error) {
			return embed(ctx, client, model, []genai.Part{genai.Text(input)})
		}), nil
}

func generate(ctx context.Context, client *genai.Client, model string, input *genkit.GenerateRequest) (*genkit.GenerateResponse, error) {
	gm := client.GenerativeModel(model)

	// Translate from a genkit.GenerateRequest to a genai request.
	gm.SetCandidateCount(int32(input.Candidates))
	if c := input.Config; c != nil {
		gm.SetMaxOutputTokens(int32(c.MaxOutputTokens))
		gm.StopSequences = c.StopSequences
		gm.SetTemperature(float32(c.Temperature))
		gm.SetTopK(int32(c.TopK))
		gm.SetTopP(float32(c.TopP))
	}

	convertPart := func(p *genkit.Part) genai.Part {
		switch {
		case p.IsPlainText():
			return genai.Text(p.Text())
		default:
			return genai.Blob{MIMEType: p.ContentType(), Data: []byte(p.Text())}
		}
	}
	convertParts := func(parts []*genkit.Part) []genai.Part {
		res := make([]genai.Part, 0, len(parts))
		for _, p := range parts {
			res = append(res, convertPart(p))
		}
		return res
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
	resp, err := cs.SendMessage(ctx, parts...)
	if err != nil {
		return nil, err
	}

	// Translate from a genai.GenerateContentResponse to a genkit.GenerateResponse.
	r := &genkit.GenerateResponse{}
	for _, cand := range resp.Candidates {
		c := &genkit.Candidate{}
		c.Index = int(cand.Index)
		switch cand.FinishReason {
		case genai.FinishReasonStop:
			c.FinishReason = genkit.FinishReasonStop
		case genai.FinishReasonMaxTokens:
			c.FinishReason = genkit.FinishReasonLength
		case genai.FinishReasonSafety:
			c.FinishReason = genkit.FinishReasonBlocked
		case genai.FinishReasonRecitation:
			c.FinishReason = genkit.FinishReasonBlocked
		case genai.FinishReasonOther:
			c.FinishReason = genkit.FinishReasonOther
		default: // Unspecified
			c.FinishReason = genkit.FinishReasonUnknown
		}
		m := &genkit.Message{}
		m.Role = genkit.Role(cand.Content.Role)
		for _, part := range cand.Content.Parts {
			var p *genkit.Part
			switch part := part.(type) {
			case genai.Text:
				p = genkit.NewTextPart(string(part))
			case genai.Blob:
				p = genkit.NewBlobPart(part.MIMEType, string(part.Data))
			case genai.FunctionResponse:
				p = genkit.NewBlobPart("TODO", string(part.Name))
			default:
				panic("unknown part type")
			}
			m.Content = append(m.Content, p)
		}
		c.Message = m
		r.Candidates = append(r.Candidates, c)
	}
	return r, nil
}

// NewGenerator returns an action which sends a request to
// the google AI model and returns the response.
func NewGenerator(ctx context.Context, model, apiKey string) (*genkit.Action[*genkit.GenerateRequest, *genkit.GenerateResponse], error) {
	client, err := newClient(ctx, apiKey)
	if err != nil {
		return nil, err
	}
	return genkit.NewAction(
		model,
		func(ctx context.Context, input *genkit.GenerateRequest) (*genkit.GenerateResponse, error) {
			return generate(ctx, client, model, input)
		}), nil
}

// Init registers all the actions in this package with genkit.
func Init(ctx context.Context, model, apiKey string) error {
	t, err := NewTextEmbedder(ctx, model, apiKey)
	if err != nil {
		return err
	}
	genkit.RegisterAction(genkit.ActionTypeEmbedder, "google-genai", t)

	g, err := NewGenerator(ctx, model, apiKey)
	if err != nil {
		return err
	}
	genkit.RegisterAction(genkit.ActionTypeModel, "google-genai", g)

	return nil
}
