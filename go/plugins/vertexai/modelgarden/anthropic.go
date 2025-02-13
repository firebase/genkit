// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelgarden

import (
	"context"
	"encoding/json"
	"fmt"
	"math"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/internal/gemini"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/vertex"
)

// supported anthropic models
var AnthropicModels = map[string]ai.ModelInfo{
	"claude-3-5-sonnet-v2": {
		Label:    "Vertex AI Model Garden - Claude 3.5 Sonnet",
		Supports: &gemini.Multimodal,
		Versions: []string{"claude-3-5-sonnet-v2@20241022"},
	},
	"claude-3-5-sonnet": {
		Label:    "Vertex AI Model Garden - Claude 3.5 Sonnet",
		Supports: &gemini.Multimodal,
		Versions: []string{"claude-3-5-sonnet@20240620"},
	},
	"claude-3-sonnet": {
		Label:    "Vertex AI Model Garden - Claude 3 Sonnet",
		Supports: &gemini.Multimodal,
		Versions: []string{"claude-3-sonnet@20240229"},
	},
	"claude-3-haiku": {
		Label:    "Vertex AI Model Garden - Claude 3 Haiku",
		Supports: &gemini.Multimodal,
		Versions: []string{"claude-3-haiku@20240307"},
	},
	"claude-3-opus": {
		Label:    "Vertex AI Model Garden - Claude 3 Opus",
		Supports: &gemini.Multimodal,
		Versions: []string{"claude-3-opus@20240229"},
	},
}

// AnthropicClientConfig is the required configuration to create an Anthropic
// client
type AnthropicClientConfig struct {
	Location string
	Project  string
}

// AnthropicClient is a mirror struct of Anthropic's client but implements
// [Client] interface
type AnthropicClient struct {
	*anthropic.Client
}

// Anthropic defines how an Anthropic client is created
var Anthropic = func(config any) (Client, error) {
	cfg, ok := config.(*AnthropicClientConfig)
	if !ok {
		return nil, fmt.Errorf("invalid config for Anthropic %T", config)
	}
	c := anthropic.NewClient(
		vertex.WithGoogleAuth(context.Background(), cfg.Location, cfg.Project),
	)

	return &AnthropicClient{c}, nil
}

// DefineModel adds the model to the registry
func (a *AnthropicClient) DefineModel(g *genkit.Genkit, name string, info *ai.ModelInfo) (ai.Model, error) {
	var mi ai.ModelInfo
	if info == nil {
		var ok bool
		mi, ok = AnthropicModels[name]
		if !ok {
			return nil, fmt.Errorf("%s.DefineModel: called with unknown model %q and nil ModelInfo", AnthropicProvider, name)
		}
	} else {
		mi = *info
	}
	return defineModel(g, a, name, mi), nil
}

func defineModel(g *genkit.Genkit, client *AnthropicClient, name string, info ai.ModelInfo) ai.Model {
	meta := &ai.ModelInfo{
		Label:    AnthropicProvider + "-" + name,
		Supports: info.Supports,
		Versions: info.Versions,
	}
	return genkit.DefineModel(g, AnthropicProvider, name, meta, func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		return generate(ctx, client, name, input, cb)
	})
}

// generate function defines how a generate request is done in Anthropic models
func generate(
	ctx context.Context,
	client *AnthropicClient,
	model string,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	// parse configuration
	req := toAnthropicRequest(model, input)

	// no streaming
	if cb == nil {
		msg, err := client.Messages.New(ctx, req)
		if err != nil {
			return nil, err
		}

		r := toGenkitResponse(msg)
		r.Request = input
		return r, nil
	} else {
		stream := client.Messages.NewStreaming(ctx, req)
		msg := anthropic.Message{}
		for stream.Next() {
			event := stream.Current()
			msg.Accumulate(event)

			switch delta := event.Delta.(type) {
			case anthropic.ContentBlockDeltaEventDelta:
				if delta.Text != "" {
					fmt.Printf(delta.Text)
				}
			}
		}
	}

	return nil, nil
}

// toAnthropicRequest translates [ai.ModelRequest] to an Anthropic request
func toAnthropicRequest(model string, i *ai.ModelRequest) anthropic.MessageNewParams {
	req := anthropic.MessageNewParams{}

	// minimum required data to perform a request
	req.Model = anthropic.F(anthropic.Model(model))
	req.MaxTokens = anthropic.F(int64(math.MaxInt64))

	if c, ok := i.Config.(*ai.GenerationCommonConfig); ok && c != nil {
		if c.MaxOutputTokens != 0 {
			req.MaxTokens = anthropic.F(int64(c.MaxOutputTokens))
		}
		req.Model = anthropic.F(anthropic.Model(model))
		if c.Version != "" {
			req.Model = anthropic.F(anthropic.Model(c.Version))
		}
		if c.Temperature != 0 {
			req.Temperature = anthropic.F(c.Temperature)
		}
		if c.TopK != 0 {
			req.TopK = anthropic.F(int64(c.TopK))
		}
		if c.TopP != 0 {
			req.TopP = anthropic.F(float64(c.TopP))
		}
		if len(c.StopSequences) > 0 {
			req.StopSequences = anthropic.F(c.StopSequences)
		}
	}
	// system and user blocks
	sysBlocks := []anthropic.TextBlockParam{}
	userBlocks := []anthropic.TextBlockParam{}
	for _, m := range i.Messages {
		// TODO: convert messages to its types (text, media, toolResponse)
		if m.Role == ai.RoleSystem {
			sysBlocks = append(sysBlocks, anthropic.NewTextBlock(m.Text()))
		}
		if m.Role == ai.RoleUser {
			userBlocks = append(userBlocks, anthropic.NewTextBlock(m.Text()))
		}
	}
	if len(sysBlocks) > 0 {
		req.System = anthropic.F(sysBlocks)
	}
	if len(userBlocks) > 0 {
		messageParam := make([]anthropic.MessageParam, 0)
		for _, u := range userBlocks {
			messageParam = append(messageParam, anthropic.NewUserMessage(u))
		}
		req.Messages = anthropic.F(messageParam)
	}

	return req
}

// toGenkitResponse translates an Anthropic Message to [ai.ModelResponse]
func toGenkitResponse(m *anthropic.Message) *ai.ModelResponse {
	r := &ai.ModelResponse{}

	switch m.StopReason {
	case anthropic.MessageStopReasonMaxTokens:
		r.FinishReason = ai.FinishReasonLength
	case anthropic.MessageStopReasonStopSequence:
		r.FinishReason = ai.FinishReasonStop
	case anthropic.MessageStopReasonEndTurn:
	case anthropic.MessageStopReasonToolUse:
		r.FinishReason = ai.FinishReasonOther
	default:
		r.FinishReason = ai.FinishReasonUnknown
	}

	msg := &ai.Message{}
	msg.Role = ai.Role(m.Role)
	for _, part := range m.Content {
		var p *ai.Part
		switch part.Type {
		case anthropic.ContentBlockTypeText:
			p = ai.NewTextPart(string(part.Text))
		case anthropic.ContentBlockTypeToolUse:
			t := &ai.ToolRequest{}
			err := json.Unmarshal([]byte(part.Input), &t.Input)
			if err != nil {
				return nil
			}
			p = ai.NewToolRequestPart(t)
		default:
			panic(fmt.Sprintf("unknown part: %#v", part))
		}
		msg.Content = append(msg.Content, p)
	}

	r.Message = msg
	return r
}
