// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package anthropic

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"github.com/invopop/jsonschema"

	"github.com/anthropics/anthropic-sdk-go"
)

const (
	maxNumberOfTokens = 4096
	toolNameRegex     = `^[a-zA-Z0-9_-]{1,64}$`
)

// configToMap converts a config struct to a map[string]any.
func configToMap(config any) map[string]any {
	r := jsonschema.Reflector{
		DoNotReference: true, // Prevent $ref usage
		ExpandedStruct: true, // Include all fields directly
	}

	schema := r.Reflect(config)
	result := base.SchemaAsMap(schema)
	return result
}

// AnthropicUIConfig represents configuration options for Anthropic models in the UI
// This includes both common generation parameters and Anthropic-specific options
type AnthropicUIConfig struct {
	// Common generation parameters
	MaxOutputTokens int      `json:"maxOutputTokens" jsonschema:"title=Max Output Tokens,description=Maximum number of tokens to generate,minimum=1,default=4096"`
	Temperature     float64  `json:"temperature" jsonschema:"title=Temperature,description=Controls randomness in generation (0.0-1.0),minimum=0,maximum=1,default=1.0"`
	TopK            int      `json:"topK" jsonschema:"title=Top K,description=Sample from top K options for each token,minimum=1,default=40"`
	TopP            float64  `json:"topP" jsonschema:"title=Top P,description=Nucleus sampling threshold (0.0-1.0),minimum=0,maximum=1,default=0.9"`
	StopSequences   []string `json:"stopSequences" jsonschema:"title=Stop Sequences,description=Custom sequences that stop generation"`

	// Anthropic-specific parameters
	UserID               string `json:"userId" jsonschema:"title=User ID,description=External identifier for the user (UUID or hash - no PII)"`
	ServiceTier          string `json:"serviceTier" jsonschema:"title=Service Tier,description=Service tier for the request,enum=auto,enum=standard_only,default=auto"`
	ThinkingEnabled      bool   `json:"thinkingEnabled" jsonschema:"title=Enable Thinking,description=Enable Claude's extended thinking process"`
	ThinkingBudgetTokens int64  `json:"thinkingBudgetTokens" jsonschema:"title=Thinking Budget Tokens,description=Token budget for thinking (minimum 1024),minimum=1024,default=2048"`

	// Anthropic server tools (pass-through to tools array)
	WebSearchEnabled        bool     `json:"webSearchEnabled" jsonschema:"title=Enable Web Search,description=Enable Anthropic's web search tool"`
	WebSearchMaxUses        int      `json:"webSearchMaxUses" jsonschema:"title=Web Search Max Uses,description=Maximum number of web searches per request,minimum=1,maximum=20,default=5"`
	WebSearchAllowedDomains []string `json:"webSearchAllowedDomains" jsonschema:"title=Web Search Allowed Domains,description=Only include results from these domains"`
	WebSearchBlockedDomains []string `json:"webSearchBlockedDomains" jsonschema:"title=Web Search Blocked Domains,description=Never include results from these domains"`
}

// newModel creates a model without registering it
func newModel(client anthropic.Client, name string, opts ai.ModelOptions) ai.Model {
	// Generate config schema using the UI-friendly configuration struct
	// This provides readable parameter names in the Developer UI
	configSchema := configToMap(&AnthropicUIConfig{})

	meta := &ai.ModelOptions{
		Label:        opts.Label,
		Supports:     opts.Supports,
		Versions:     opts.Versions,
		ConfigSchema: configSchema,
		Stage:        opts.Stage,
	}

	fn := func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		return anthropicGenerate(ctx, client, name, input, cb)
	}

	return ai.NewModel(api.NewName(anthropicProvider, name), meta, fn)
}

// anthropicGenerate handles the generation request to Anthropic API
func anthropicGenerate(
	ctx context.Context,
	client anthropic.Client,
	model string,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	req, err := toAnthropicRequest(model, input)
	if err != nil {
		return nil, fmt.Errorf("unable to generate anthropic request: %w", err)
	}

	// Non-streaming request
	if cb == nil {
		msg, err := client.Messages.New(ctx, *req)
		if err != nil {
			return nil, err
		}

		r, err := anthropicToGenkitResponse(msg)
		if err != nil {
			return nil, err
		}

		r.Request = input
		return r, nil
	}

	// Streaming request
	stream := client.Messages.NewStreaming(ctx, *req)
	message := anthropic.Message{}
	for stream.Next() {
		event := stream.Current()
		err := message.Accumulate(event)
		if err != nil {
			return nil, err
		}

		switch event := event.AsAny().(type) {
		case anthropic.ContentBlockDeltaEvent:
			err := cb(ctx, &ai.ModelResponseChunk{
				Content: []*ai.Part{
					ai.NewTextPart(event.Delta.Text),
				},
			})
			if err != nil {
				return nil, err
			}
		case anthropic.MessageStopEvent:
			r, err := anthropicToGenkitResponse(&message)
			if err != nil {
				return nil, err
			}
			r.Request = input
			return r, nil
		}
	}
	if stream.Err() != nil {
		return nil, stream.Err()
	}

	return nil, nil
}

// toAnthropicRequest translates [ai.ModelRequest] to an Anthropic request
func toAnthropicRequest(model string, i *ai.ModelRequest) (*anthropic.MessageNewParams, error) {
	messages := make([]anthropic.MessageParam, 0)

	c, err := configFromRequest(i)
	if err != nil {
		return nil, err
	}

	// Start with minimum required data
	req := anthropic.MessageNewParams{}
	req.Model = anthropic.Model(model)
	req.MaxTokens = int64(maxNumberOfTokens)

	// Apply Genkit common configuration
	if c.MaxOutputTokens != 0 {
		req.MaxTokens = int64(c.MaxOutputTokens)
	}
	if c.Version != "" {
		req.Model = anthropic.Model(c.Version)
	}
	if c.Temperature != 0 {
		req.Temperature = anthropic.Float(c.Temperature)
	}
	if c.TopK != 0 {
		req.TopK = anthropic.Int(int64(c.TopK))
	}
	if c.TopP != 0 {
		req.TopP = anthropic.Float(float64(c.TopP))
	}
	if len(c.StopSequences) > 0 {
		req.StopSequences = c.StopSequences
	}

	// configure system prompt (if given)
	sysBlocks := []anthropic.TextBlockParam{}
	for _, message := range i.Messages {
		if message.Role == ai.RoleSystem {
			// only text is supported for system messages
			sysBlocks = append(sysBlocks, anthropic.TextBlockParam{Text: message.Text()})
		} else if len(message.Content) > 0 && message.Content[len(message.Content)-1].IsToolResponse() {
			// if the last message is a ToolResponse, the conversation must continue
			// and the ToolResponse message must be sent as a user
			// see: https://docs.anthropic.com/en/docs/build-with-claude/tool-use#handling-tool-use-and-tool-result-content-blocks
			parts, err := toAnthropicParts(message.Content)
			if err != nil {
				return nil, err
			}
			messages = append(messages, anthropic.NewUserMessage(parts...))
		} else {
			parts, err := toAnthropicParts(message.Content)
			if err != nil {
				return nil, err
			}
			role, err := toAnthropicRole(message.Role)
			if err != nil {
				return nil, err
			}
			messages = append(messages, anthropic.MessageParam{
				Role:    role,
				Content: parts,
			})
		}
	}

	req.System = sysBlocks
	req.Messages = messages

	tools, err := toAnthropicTools(i.Tools)
	if err != nil {
		return nil, err
	}
	req.Tools = tools

	// Handle pass-through parameters for map-based config
	// This must be done AFTER setting the tools to avoid overwriting web search tools
	if mapConfig, ok := i.Config.(map[string]any); ok {
		if err := applyPassThroughConfig(&req, mapConfig); err != nil {
			return nil, fmt.Errorf("failed to apply pass-through config: %w", err)
		}
	}

	return &req, nil
}

// AnthropicConfig represents the full configuration options available for Anthropic models
// This includes both Genkit common options and Anthropic-specific parameters
type AnthropicConfig struct {
	ai.GenerationCommonConfig

	// Anthropic-specific parameters that can be passed through
	Metadata map[string]any `json:"metadata,omitempty"`
	// Add other Anthropic-specific fields as needed
}

// configFromRequest converts any supported config type to [AnthropicConfig]
func configFromRequest(input *ai.ModelRequest) (*AnthropicConfig, error) {
	var result AnthropicConfig

	switch config := input.Config.(type) {
	case AnthropicConfig:
		result = config
	case *AnthropicConfig:
		result = *config
	case ai.GenerationCommonConfig:
		result.GenerationCommonConfig = config
	case *ai.GenerationCommonConfig:
		result.GenerationCommonConfig = *config
	case map[string]any:
		// First try to unmarshal into AnthropicConfig to capture all fields
		if err := mapToStruct(config, &result); err != nil {
			// If that fails, try just the common config
			if err := mapToStruct(config, &result.GenerationCommonConfig); err != nil {
				return nil, err
			}
		}
	case nil:
		// Empty configuration is considered valid
	default:
		return nil, fmt.Errorf("unexpected config type: %T", input.Config)
	}
	return &result, nil
}

// mapToStruct unmarshals a map[String]any to the expected type
func mapToStruct(m map[string]any, v any) error {
	jsonData, err := json.Marshal(m)
	if err != nil {
		return err
	}
	return json.Unmarshal(jsonData, v)
}

// applyPassThroughConfig applies configuration parameters from the UI config
// This handles both common generation parameters and Anthropic-specific parameters
func applyPassThroughConfig(req *anthropic.MessageNewParams, config map[string]any) error {
	// Handle common generation parameters
	if maxTokens, exists := config["maxOutputTokens"]; exists {
		if tokens, ok := maxTokens.(float64); ok && tokens > 0 {
			req.MaxTokens = int64(tokens)
		} else if tokens, ok := maxTokens.(int); ok && tokens > 0 {
			req.MaxTokens = int64(tokens)
		}
	}

	if temperature, exists := config["temperature"]; exists {
		if temp, ok := temperature.(float64); ok {
			req.Temperature = anthropic.Float(temp)
		}
	}

	if topK, exists := config["topK"]; exists {
		if k, ok := topK.(float64); ok && k > 0 {
			req.TopK = anthropic.Int(int64(k))
		} else if k, ok := topK.(int); ok && k > 0 {
			req.TopK = anthropic.Int(int64(k))
		}
	}

	if topP, exists := config["topP"]; exists {
		if p, ok := topP.(float64); ok {
			req.TopP = anthropic.Float(p)
		}
	}

	if stopSeqs, exists := config["stopSequences"]; exists {
		if sequences, ok := stopSeqs.([]interface{}); ok {
			var stopSequences []string
			for _, seq := range sequences {
				if seqStr, ok := seq.(string); ok {
					stopSequences = append(stopSequences, seqStr)
				}
			}
			if len(stopSequences) > 0 {
				req.StopSequences = stopSequences
			}
		}
	}

	// Handle User ID for metadata
	if userID, exists := config["userId"]; exists {
		if userIDStr, ok := userID.(string); ok && userIDStr != "" {
			req.Metadata = anthropic.MetadataParam{
				UserID: anthropic.String(userIDStr),
			}
		}
	}

	// Handle Service Tier
	if serviceTier, exists := config["serviceTier"]; exists {
		if serviceTierStr, ok := serviceTier.(string); ok && serviceTierStr != "" {
			switch serviceTierStr {
			case "auto":
				req.ServiceTier = anthropic.MessageNewParamsServiceTierAuto
			case "standard_only":
				req.ServiceTier = anthropic.MessageNewParamsServiceTierStandardOnly
			}
		}
	}

	// Handle Extended Thinking configuration
	if thinkingEnabled, exists := config["thinkingEnabled"]; exists {
		if enabled, ok := thinkingEnabled.(bool); ok && enabled {
			// Default budget tokens if not specified
			budgetTokens := int64(2048)

			// Check if custom budget is specified
			if budgetTokensVal, budgetExists := config["thinkingBudgetTokens"]; budgetExists {
				if budget, ok := budgetTokensVal.(float64); ok && budget >= 1024 {
					budgetTokens = int64(budget)
				} else if budget, ok := budgetTokensVal.(int64); ok && budget >= 1024 {
					budgetTokens = budget
				} else if budget, ok := budgetTokensVal.(int); ok && budget >= 1024 {
					budgetTokens = int64(budget)
				}
			}

			req.Thinking = anthropic.ThinkingConfigParamOfEnabled(budgetTokens)
		}
	}

	// Handle Web Search tool configuration
	if webSearchEnabled, exists := config["webSearchEnabled"]; exists {
		if enabled, ok := webSearchEnabled.(bool); ok && enabled {
			webSearchTool := anthropic.ToolUnionParam{
				OfWebSearchTool20250305: &anthropic.WebSearchTool20250305Param{},
			}

			// Set max uses if specified
			if maxUsesVal, maxUsesExists := config["webSearchMaxUses"]; maxUsesExists {
				if maxUses, ok := maxUsesVal.(float64); ok && maxUses > 0 {
					webSearchTool.OfWebSearchTool20250305.MaxUses = anthropic.Int(int64(maxUses))
				} else if maxUses, ok := maxUsesVal.(int); ok && maxUses > 0 {
					webSearchTool.OfWebSearchTool20250305.MaxUses = anthropic.Int(int64(maxUses))
				}
			}

			// Set allowed domains if specified
			if allowedDomainsVal, allowedExists := config["webSearchAllowedDomains"]; allowedExists {
				if domains, ok := allowedDomainsVal.([]interface{}); ok {
					var allowedDomains []string
					for _, domain := range domains {
						if domainStr, ok := domain.(string); ok && domainStr != "" {
							allowedDomains = append(allowedDomains, domainStr)
						}
					}
					if len(allowedDomains) > 0 {
						webSearchTool.OfWebSearchTool20250305.AllowedDomains = allowedDomains
					}
				}
			}

			// Set blocked domains if specified
			if blockedDomainsVal, blockedExists := config["webSearchBlockedDomains"]; blockedExists {
				if domains, ok := blockedDomainsVal.([]interface{}); ok {
					var blockedDomains []string
					for _, domain := range domains {
						if domainStr, ok := domain.(string); ok && domainStr != "" {
							blockedDomains = append(blockedDomains, domainStr)
						}
					}
					if len(blockedDomains) > 0 {
						webSearchTool.OfWebSearchTool20250305.BlockedDomains = blockedDomains
					}
				}
			}

			// Add the web search tool to the request
			req.Tools = append(req.Tools, webSearchTool)
		}
	}

	return nil
}

// toAnthropicRole converts ai.Role to anthropic.MessageParamRole
func toAnthropicRole(role ai.Role) (anthropic.MessageParamRole, error) {
	switch role {
	case ai.RoleUser:
		return anthropic.MessageParamRoleUser, nil
	case ai.RoleModel:
		return anthropic.MessageParamRoleAssistant, nil
	case ai.RoleTool:
		return anthropic.MessageParamRoleAssistant, nil
	default:
		return "", fmt.Errorf("unknown role given: %q", role)
	}
}

// toAnthropicTools translates [ai.ToolDefinition] to an anthropic.ToolParam type
func toAnthropicTools(tools []*ai.ToolDefinition) ([]anthropic.ToolUnionParam, error) {
	resp := make([]anthropic.ToolUnionParam, 0)
	regex := regexp.MustCompile(toolNameRegex)

	for _, t := range tools {
		if t.Name == "" {
			return nil, fmt.Errorf("tool name is required")
		}
		if !regex.MatchString(t.Name) {
			return nil, fmt.Errorf("tool name must match regex: %s", toolNameRegex)
		}

		resp = append(resp, anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        t.Name,
				Description: anthropic.String(t.Description),
				InputSchema: toAnthropicSchema[map[string]any](),
			},
		})
	}

	return resp, nil
}

// toAnthropicSchema generates a JSON schema for the requested input type
func toAnthropicSchema[T any]() anthropic.ToolInputSchemaParam {
	reflector := jsonschema.Reflector{
		AllowAdditionalProperties: true,
		DoNotReference:            true,
	}
	var v T
	schema := reflector.Reflect(v)
	return anthropic.ToolInputSchemaParam{
		Properties: schema.Properties,
	}
}

// downloadImageFromURL downloads an image from a URL and returns the content type and data
func downloadImageFromURL(url string) (string, []byte, error) {
	resp, err := http.Get(url)
	if err != nil {
		return "", nil, fmt.Errorf("failed to download image: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", nil, fmt.Errorf("failed to download image: HTTP %d", resp.StatusCode)
	}

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", nil, fmt.Errorf("failed to read image data: %w", err)
	}

	// Get content type from response header
	contentType := resp.Header.Get("Content-Type")
	if contentType == "" {
		// Try to infer from URL extension
		if strings.Contains(strings.ToLower(url), ".png") {
			contentType = "image/png"
		} else if strings.Contains(strings.ToLower(url), ".jpg") || strings.Contains(strings.ToLower(url), ".jpeg") {
			contentType = "image/jpeg"
		} else if strings.Contains(strings.ToLower(url), ".gif") {
			contentType = "image/gif"
		} else if strings.Contains(strings.ToLower(url), ".webp") {
			contentType = "image/webp"
		} else {
			// Default to JPEG if we can't determine
			contentType = "image/jpeg"
		}
	}

	return contentType, data, nil
}

// toAnthropicParts translates [ai.Part] to an anthropic.ContentBlockParamUnion type
func toAnthropicParts(parts []*ai.Part) ([]anthropic.ContentBlockParamUnion, error) {
	blocks := []anthropic.ContentBlockParamUnion{}

	for _, p := range parts {
		switch {
		case p.IsText():
			blocks = append(blocks, anthropic.NewTextBlock(p.Text))
		case p.IsMedia():
			// Check if this is an HTTP URL that needs custom downloading
			if strings.HasPrefix(p.Text, "http://") || strings.HasPrefix(p.Text, "https://") {
				contentType, data, err := downloadImageFromURL(p.Text)
				if err != nil {
					return nil, fmt.Errorf("failed to download image from URL %s: %w", p.Text, err)
				}
				blocks = append(blocks, anthropic.NewImageBlockBase64(contentType, base64.StdEncoding.EncodeToString(data)))
			} else {
				// Use the original uri.Data for non-HTTP URLs (file://, data:, etc.)
				contentType, data, err := uri.Data(p)
				if err != nil {
					return nil, err
				}
				blocks = append(blocks, anthropic.NewImageBlockBase64(contentType, base64.StdEncoding.EncodeToString(data)))
			}
		case p.IsData():
			// Check if this is an HTTP URL that needs custom downloading
			if strings.HasPrefix(p.Text, "http://") || strings.HasPrefix(p.Text, "https://") {
				contentType, data, err := downloadImageFromURL(p.Text)
				if err != nil {
					return nil, fmt.Errorf("failed to download image from URL %s: %w", p.Text, err)
				}
				blocks = append(blocks, anthropic.NewImageBlockBase64(contentType, base64.StdEncoding.EncodeToString(data)))
			} else {
				// Use the original uri.Data for non-HTTP URLs (file://, data:, etc.)
				contentType, data, err := uri.Data(p)
				if err != nil {
					return nil, err
				}
				blocks = append(blocks, anthropic.NewImageBlockBase64(contentType, base64.RawStdEncoding.EncodeToString(data)))
			}
		case p.IsToolRequest():
			toolReq := p.ToolRequest
			blocks = append(blocks, anthropic.NewToolUseBlock(toolReq.Ref, toolReq.Input, toolReq.Name))
		case p.IsToolResponse():
			toolResp := p.ToolResponse
			output, err := json.Marshal(toolResp.Output)
			if err != nil {
				return nil, fmt.Errorf("unable to parse tool response, err: %w", err)
			}
			blocks = append(blocks, anthropic.NewToolResultBlock(toolResp.Ref, string(output), false))
		default:
			return nil, errors.New("unknown part type in the request")
		}
	}

	return blocks, nil
}

// anthropicToGenkitResponse translates an Anthropic Message to [ai.ModelResponse]
func anthropicToGenkitResponse(m *anthropic.Message) (*ai.ModelResponse, error) {
	r := ai.ModelResponse{}

	switch m.StopReason {
	case anthropic.StopReasonMaxTokens:
		r.FinishReason = ai.FinishReasonLength
	case anthropic.StopReasonStopSequence:
		r.FinishReason = ai.FinishReasonStop
	case anthropic.StopReasonEndTurn:
		r.FinishReason = ai.FinishReasonStop
	case anthropic.StopReasonToolUse:
		r.FinishReason = ai.FinishReasonStop
	default:
		r.FinishReason = ai.FinishReasonUnknown
	}

	msg := &ai.Message{}
	msg.Role = ai.RoleModel
	for _, part := range m.Content {
		var p *ai.Part
		switch partType := part.AsAny().(type) {
		case anthropic.TextBlock:
			p = ai.NewTextPart(string(part.Text))
		case anthropic.ToolUseBlock:
			p = ai.NewToolRequestPart(&ai.ToolRequest{
				Ref:   part.ID,
				Input: part.Input,
				Name:  part.Name,
			})
		case anthropic.WebSearchToolResultBlock:
			// Handle web search tool results - extract the search results and format them as text
			resultText := fmt.Sprintf("Web search results for query: %s\n", part.Name)
			if part.Content.OfWebSearchResultBlockArray != nil {
				for i, result := range part.Content.OfWebSearchResultBlockArray {
					resultText += fmt.Sprintf("\n%d. %s\n   URL: %s\n   Age: %s\n",
						i+1, result.Title, result.URL, result.PageAge)
				}
			}
			p = ai.NewTextPart(resultText)
		default:
			// Handle server-side tools (like web search) by checking the Type field
			if part.Type == "server_tool_use" {
				// For server-side tools, we treat them as text responses since they're executed server-side
				// and the results are included in the response
				p = ai.NewTextPart(fmt.Sprintf("Used %s tool with query: %s", part.Name, string(part.Input)))
			} else if part.Type == "web_search_tool_result" {
				// Handle web search tool results as text
				p = ai.NewTextPart("Web search completed with results")
			} else {
				return nil, fmt.Errorf("unknown part type '%s': %#v", part.Type, partType)
			}
		}
		msg.Content = append(msg.Content, p)
	}

	r.Message = msg
	r.Usage = &ai.GenerationUsage{
		InputTokens:  int(m.Usage.InputTokens),
		OutputTokens: int(m.Usage.OutputTokens),
	}
	return &r, nil
}
