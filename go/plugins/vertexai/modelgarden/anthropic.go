// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelgarden

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/internal/gemini"
	"github.com/firebase/genkit/go/plugins/internal/uri"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/vertex"
)

const MaxNumberOfTokens = 8192

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
					fmt.Print(delta.Text)
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
	req.MaxTokens = anthropic.F(int64(MaxNumberOfTokens))

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

	// check user and system messages
	sysBlocks := []anthropic.TextBlockParam{}
	userBlocks := []anthropic.ContentBlockParamUnion{}
	for _, m := range i.Messages {
		switch m.Role {
		case ai.RoleSystem:
			// text blocks only supported for system messages
			sysBlocks = append(sysBlocks, anthropic.NewTextBlock(m.Text()))
		case ai.RoleUser:
			parts, err := convertParts(m.Content)
			if err != nil {
				return req
			}
			userBlocks = append(userBlocks, parts...)
		}
	}

	if len(sysBlocks) > 0 {
		req.System = anthropic.F(sysBlocks)
	}
	if len(userBlocks) > 0 {
		messageParam := make([]anthropic.MessageParam, 0, len(userBlocks))
		for _, m := range userBlocks {
			messageParam = append(messageParam, anthropic.NewUserMessage(m))
		}
		req.Messages = anthropic.F(messageParam)
	}

	return req
}

// convertParts translates [ai.Part] to an anthropic.ContentBlockParamUnion type
func convertParts(parts []*ai.Part) ([]anthropic.ContentBlockParamUnion, error) {
	blocks := []anthropic.ContentBlockParamUnion{}

	for _, p := range parts {
		switch {
		case p.IsText():
			blocks = append(blocks, anthropic.NewTextBlock(p.Text))
		case p.IsMedia():
			// TODO: check this
			contentType, data, _ := uri.Data(p)
			blocks = append(blocks, anthropic.NewImageBlockBase64(contentType, string(data)))
		case p.IsData():
			// todo: what is this? is this related to ContentBlocks?
			panic("data content is unsupported by anthropic models")
		case p.IsToolResponse():
			// TODO: check this
			toolResp := p.ToolResponse
			if toolResp.Output == nil {
				panic("tool response is empty")
			}
			data, err := json.Marshal(toolResp.Output)
			if err != nil {
				panic("unable to parse tool response")
			}
			blocks = append(blocks, anthropic.NewToolResultBlock(toolResp.Name, string(data), false))
		case p.IsToolRequest():
			// TODO: check this
			toolReq := p.ToolRequest
			blocks = append(blocks, anthropic.NewToolUseBlockParam(toolReq.Name, toolReq.Name, toolReq.Input))
		default:
			panic("unknown part type in the request")
		}
	}

	return blocks, nil
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
