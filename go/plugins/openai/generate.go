package openai

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/openai/openai-go"
)

// Generator handles OpenAI generation requests
type Generator struct {
	client    *openai.Client
	modelName string
	request   *openai.ChatCompletionNewParams
}

// NewGenerator creates a new Generator instance
func NewGenerator(client *openai.Client, modelName string) *Generator {
	return &Generator{
		client:    client,
		modelName: modelName,
		request: &openai.ChatCompletionNewParams{
			Model: openai.F(modelName),
		},
	}
}

// WithMessages adds messages to the request
func (g *Generator) WithMessages(messages []*ai.Message) *Generator {
	oaiMessages := make([]openai.ChatCompletionMessageParamUnion, 0, len(messages))
	for _, msg := range messages {
		content := g.concatenateContent(msg.Content)
		switch msg.Role {
		case ai.RoleSystem:
			oaiMessages = append(oaiMessages, openai.SystemMessage(content))
		case ai.RoleModel:
			oaiMessages = append(oaiMessages, openai.AssistantMessage(content))
		case ai.RoleTool:
			oaiMessages = append(oaiMessages, openai.ToolMessage("", content)) // TODO: Add tool ID if needed
		default:
			oaiMessages = append(oaiMessages, openai.UserMessage(content))
		}
	}
	g.request.Messages = openai.F(oaiMessages)
	return g
}

// WithConfig adds configuration parameters from the model request
func (g *Generator) WithConfig(modelRequest *ai.ModelRequest) *Generator {
	if modelRequest.Config != nil {
		// TODO: Implement configuration from model request
		// modelRequest.Config is any type
	}
	return g
}

// WithTools adds tools to the request
func (g *Generator) WithTools(tools []ai.Tool, choice ai.ToolChoice) *Generator {
	if len(tools) > 0 {
		oaiTools := make([]openai.ChatCompletionToolParam, 0, len(tools))
		for _, t := range tools {
			oaiTools = append(oaiTools, openai.ChatCompletionToolParam{
				Type: openai.F(openai.ChatCompletionToolTypeFunction),
				Function: openai.F(openai.FunctionDefinitionParam{
					Name:        openai.F(t.Name()),
					Description: openai.F(t.Description()),
					Parameters:  openai.F(t.Schema()),
				}),
			})
		}
		g.request.Tools = openai.F(oaiTools)

		switch choice {
		case ai.ToolChoiceAuto:
			g.request.ToolChoice = openai.F("auto")
		case ai.ToolChoiceNone:
			g.request.ToolChoice = openai.F("none")
		}
	}
	return g
}

// Generate executes the generation request
func (g *Generator) Generate(ctx context.Context, cb func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	if cb != nil {
		return g.generateStream(ctx, cb)
	}
	return g.generateSync(ctx)
}

func (g *Generator) concatenateContent(parts []*ai.Part) string {
	content := ""
	for _, part := range parts {
		content += part.Text
	}
	return content
}

// Private generation methods
func (g *Generator) generateStream(ctx context.Context, cb func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	stream := g.client.Chat.Completions.NewStreaming(ctx, *g.request)
	defer stream.Close()

	var fullResponse ai.ModelResponse
	fullResponse.Message = &ai.Message{
		Role:    ai.RoleAssistant,
		Content: make([]*ai.Part, 0),
	}

	for stream.Next() {
		chunk := stream.Current()
		if len(chunk.Choices) > 0 {
			content := chunk.Choices[0].Delta.Content
			modelChunk := &ai.ModelResponseChunk{
				Content: []*ai.Part{ai.NewTextPart(content)},
			}

			if err := cb(ctx, modelChunk); err != nil {
				return nil, fmt.Errorf("callback error: %w", err)
			}

			fullResponse.Message.Content = append(fullResponse.Message.Content, modelChunk.Content...)
		}
	}

	if err := stream.Err(); err != nil {
		return nil, fmt.Errorf("stream error: %w", err)
	}

	return &fullResponse, nil
}

func (g *Generator) generateSync(ctx context.Context) (*ai.ModelResponse, error) {
	completion, err := g.client.Chat.Completions.New(ctx, *g.request)
	if err != nil {
		return nil, fmt.Errorf("failed to create completion: %w", err)
	}

	return &ai.ModelResponse{
		Message: &ai.Message{
			Role: ai.RoleAssistant,
			Content: []*ai.Part{
				ai.NewTextPart(completion.Choices[0].Message.Content),
			},
		},
		FinishReason: string(completion.Choices[0].FinishReason),
		Usage: &ai.Usage{
			InputTokens:  completion.Usage.PromptTokens,
			OutputTokens: completion.Usage.CompletionTokens,
			TotalTokens:  completion.Usage.TotalTokens,
		},
	}, nil
}
