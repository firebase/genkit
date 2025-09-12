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
	"os"
	"regexp"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"github.com/invopop/jsonschema"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/option"
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

	// Code Execution configuration
	CodeExecutionEnabled bool `json:"codeExecutionEnabled" jsonschema:"title=Enable Code Execution,description=Enable Claude's code execution capabilities"`

	// Beta API configuration
	UseBetaAPI bool `json:"useBetaAPI" jsonschema:"title=Use Beta API,description=Explicitly enable Anthropic Beta API features"`
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
	// Check if beta API is enabled to determine which API to use
	if isBetaApiEnabled(input.Config) {
		// Use Beta API for beta features (code execution, etc.)
		return anthropicGenerateBeta(ctx, client, model, input, cb)
	}

	// Use regular API for non-code-execution requests
	req, err := toAnthropicRegularRequest(model, input)
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

// anthropicGenerateBeta handles Beta API requests for beta features
func anthropicGenerateBeta(
	ctx context.Context,
	client anthropic.Client,
	model string,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	betaReq, err := toAnthropicBetaRequest(model, input)
	if err != nil {
		return nil, fmt.Errorf("unable to generate anthropic beta request: %w", err)
	}

	// Create a new client with the Beta API header for code execution
	// This is necessary because the code execution feature requires the specific beta header
	betaClientWithHeader := anthropic.NewClient(
		option.WithAPIKey(os.Getenv("ANTHROPIC_API_KEY")),
		option.WithHeader("anthropic-beta", "code-execution-2025-08-25"),
	)
	betaClient := betaClientWithHeader.Beta

	// Non-streaming request
	if cb == nil {
		msg, err := betaClient.Messages.New(ctx, *betaReq)
		if err != nil {
			return nil, err
		}

		r, err := anthropicBetaToGenkitResponse(msg)
		if err != nil {
			return nil, err
		}

		r.Request = input
		return r, nil
	}

	// Streaming request for Beta API
	stream := betaClient.Messages.NewStreaming(ctx, *betaReq)
	message := anthropic.BetaMessage{}
	for stream.Next() {
		event := stream.Current()
		err := message.Accumulate(event)
		if err != nil {
			return nil, err
		}

		switch event := event.AsAny().(type) {
		case anthropic.BetaRawContentBlockDeltaEvent:
			err := cb(ctx, &ai.ModelResponseChunk{
				Content: []*ai.Part{
					ai.NewTextPart(event.Delta.Text),
				},
			})
			if err != nil {
				return nil, err
			}
		case anthropic.BetaRawMessageStopEvent:
			r, err := anthropicBetaToGenkitResponse(&message)
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

// anthropicBetaToGenkitResponse translates a Beta API Message to [ai.ModelResponse]
func anthropicBetaToGenkitResponse(m *anthropic.BetaMessage) (*ai.ModelResponse, error) {
	r := ai.ModelResponse{}

	switch m.StopReason {
	case anthropic.BetaStopReasonMaxTokens:
		r.FinishReason = ai.FinishReasonLength
	case anthropic.BetaStopReasonStopSequence:
		r.FinishReason = ai.FinishReasonStop
	case anthropic.BetaStopReasonEndTurn:
		r.FinishReason = ai.FinishReasonStop
	case anthropic.BetaStopReasonToolUse:
		r.FinishReason = ai.FinishReasonStop
	default:
		r.FinishReason = ai.FinishReasonUnknown
	}

	msg := &ai.Message{}
	msg.Role = ai.RoleModel
	for _, part := range m.Content {
		var p *ai.Part
		switch part.AsAny().(type) {
		case anthropic.BetaTextBlock:
			p = ai.NewTextPart(string(part.Text))
		case anthropic.BetaToolUseBlock:
			p = ai.NewToolRequestPart(&ai.ToolRequest{
				Ref:   part.ID,
				Input: part.Input,
				Name:  part.Name,
			})
		default:
			// Conditional debug logging - only enabled when ANTHROPIC_DEBUG environment variable is set
			if os.Getenv("ANTHROPIC_DEBUG") != "" {
				fmt.Printf("DEBUG: Unknown part - Type: %q, Text: %q, ID: %q, Name: %q\n", part.Type, part.Text, part.ID, part.Name)
				if partBytes, err := json.Marshal(part); err == nil {
					fmt.Printf("DEBUG: Complete part JSON: %s\n", string(partBytes))
				}
			}

			// Handle server-side tools and other Beta-specific content types by checking the Type field
			if part.Type == "server_tool_use" {
				// Check if this is a code execution tool use
				if part.Name == "bash_code_execution" || part.Name == "text_editor_code_execution" {
					// Extract the code from the input and create an executable code part
					p = createExecutableCodePartFromToolUse(part)
				} else {
					// Other server-side tools (like web search)
					p = ai.NewCustomPart(map[string]any{
						"serverToolUse": map[string]any{
							"id":    part.ID,
							"name":  part.Name,
							"input": part.Input,
							"type":  part.Type,
						},
					})
				}
			} else if part.Type == "bash_code_execution_tool_result" {
				// Handle bash code execution results - extract the actual execution data
				if os.Getenv("ANTHROPIC_DEBUG") != "" {
					fmt.Printf("DEBUG: Found bash_code_execution_tool_result with text: %q\n", part.Text)
				}
				p = createCodeExecutionResultPartFromToolResult(part)
			} else if part.Type == "text_editor_code_execution_tool_result" {
				// Handle text editor code execution results - extract the actual execution data
				if os.Getenv("ANTHROPIC_DEBUG") != "" {
					fmt.Printf("DEBUG: Found text_editor_code_execution_tool_result with text: %q\n", part.Text)
				}
				p = createCodeExecutionResultPartFromToolResult(part)
			} else if strings.Contains(part.Type, "code_execution") && strings.Contains(part.Type, "result") {
				// Handle any other code execution result types that might exist
				// This catches variations like "code_execution_result", "python_code_execution_result", etc.
				if os.Getenv("ANTHROPIC_DEBUG") != "" {
					fmt.Printf("DEBUG: Found generic code_execution result type: %q with text: %q\n", part.Type, part.Text)
				}
				p = createCodeExecutionResultPartFromToolResult(part)
			} else if part.Type == "text" && part.Text != "" {
				p = ai.NewTextPart(part.Text)
			} else {
				// For unknown types, convert to text to avoid crashing
				p = ai.NewTextPart(fmt.Sprintf("Unknown content type '%s': %s", part.Type, part.Text))
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

// ============================================================================
// Configuration Helper Functions
// ============================================================================

// isBetaApiEnabled checks if beta API should be used based on configuration
func isBetaApiEnabled(config any) bool {
	if mapConfig, ok := config.(map[string]any); ok {
		// Check explicit useBetaAPI flag first - this takes precedence
		if useBetaAPI, exists := mapConfig["useBetaAPI"]; exists {
			if enabled, ok := useBetaAPI.(bool); ok {
				return enabled // Explicit setting always wins
			}
		}

		// Auto-enable beta mode for code execution only if useBetaAPI is not explicitly set
		if codeExecutionEnabled, exists := mapConfig["codeExecutionEnabled"]; exists {
			if enabled, ok := codeExecutionEnabled.(bool); ok && enabled {
				return true
			}
		}
	}
	return false
}

// applyCommonConfig applies common configuration parameters to both regular and Beta API requests
// Returns the basic config values that can be applied to both API types
func applyCommonConfig(c *AnthropicConfig, model string) (anthropic.Model, int64, []string) {
	// Start with defaults
	finalModel := anthropic.Model(model)
	maxTokens := int64(maxNumberOfTokens)
	var stopSequences []string

	// Apply configuration
	if c.MaxOutputTokens != 0 {
		maxTokens = int64(c.MaxOutputTokens)
	}
	if c.Version != "" {
		finalModel = anthropic.Model(c.Version)
	}
	if len(c.StopSequences) > 0 {
		stopSequences = c.StopSequences
	}

	return finalModel, maxTokens, stopSequences
}

// applyRegularAPIConfig applies configuration specific to regular API
func applyRegularAPIConfig(req *anthropic.MessageNewParams, c *AnthropicConfig) {
	if c.Temperature != 0 {
		req.Temperature = anthropic.Float(c.Temperature)
	}
	if c.TopK != 0 {
		req.TopK = anthropic.Int(int64(c.TopK))
	}
	if c.TopP != 0 {
		req.TopP = anthropic.Float(float64(c.TopP))
	}
}

// applyBetaAPIConfig applies configuration specific to Beta API
func applyBetaAPIConfig(req *anthropic.BetaMessageNewParams, c *AnthropicConfig) {
	if c.Temperature != 0 {
		req.Temperature = anthropic.Float(c.Temperature)
	}
	if c.TopK != 0 {
		req.TopK = anthropic.Int(int64(c.TopK))
	}
	if c.TopP != 0 {
		req.TopP = anthropic.Float(float64(c.TopP))
	}
}

// ============================================================================
// Request Creation Functions
// ============================================================================

// toAnthropicRegularRequest handles regular (non-Beta) API requests
func toAnthropicRegularRequest(model string, i *ai.ModelRequest) (*anthropic.MessageNewParams, error) {
	c, err := configFromRequest(i)
	if err != nil {
		return nil, err
	}

	// Apply common configuration
	finalModel, maxTokens, stopSequences := applyCommonConfig(c, model)

	// Start with minimum required data
	req := anthropic.MessageNewParams{
		Model:         finalModel,
		MaxTokens:     maxTokens,
		StopSequences: stopSequences,
	}

	// Apply regular API specific configuration
	applyRegularAPIConfig(&req, c)

	// Process messages
	messages, sysBlocks, err := processRegularMessages(i.Messages)
	if err != nil {
		return nil, err
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

// ============================================================================
// Message Processing Helper Functions
// ============================================================================

// processRegularMessages processes messages for regular API
func processRegularMessages(messages []*ai.Message) ([]anthropic.MessageParam, []anthropic.TextBlockParam, error) {
	var msgParams []anthropic.MessageParam
	var sysBlocks []anthropic.TextBlockParam

	for _, message := range messages {
		if message.Role == ai.RoleSystem {
			// only text is supported for system messages
			sysBlocks = append(sysBlocks, anthropic.TextBlockParam{Text: message.Text()})
		} else if len(message.Content) > 0 && message.Content[len(message.Content)-1].IsToolResponse() {
			// if the last message is a ToolResponse, the conversation must continue
			// and the ToolResponse message must be sent as a user
			// see: https://docs.anthropic.com/en/docs/build-with-claude/tool-use#handling-tool-use-and-tool-result-content-blocks
			parts, err := toAnthropicParts(message.Content)
			if err != nil {
				return nil, nil, err
			}
			msgParams = append(msgParams, anthropic.NewUserMessage(parts...))
		} else {
			parts, err := toAnthropicParts(message.Content)
			if err != nil {
				return nil, nil, err
			}
			role, err := toAnthropicRole(message.Role)
			if err != nil {
				return nil, nil, err
			}
			msgParams = append(msgParams, anthropic.MessageParam{
				Role:    role,
				Content: parts,
			})
		}
	}

	return msgParams, sysBlocks, nil
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

// Helper functions for configuration consolidation

// applyCommonPassThroughParams applies common generation parameters from config
func applyCommonPassThroughParams(req *anthropic.MessageNewParams, config map[string]any) {
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
}

// applyAnthropicSpecificParams applies Anthropic-specific parameters from config
func applyAnthropicSpecificParams(req *anthropic.MessageNewParams, config map[string]any) {
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
			budgetTokens := getThinkingBudgetTokens(config)
			req.Thinking = anthropic.ThinkingConfigParamOfEnabled(budgetTokens)
		}
	}
}

// getThinkingBudgetTokens extracts thinking budget tokens from config with validation
func getThinkingBudgetTokens(config map[string]any) int64 {
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

	return budgetTokens
}

// applyWebSearchConfig applies web search tool configuration
func applyWebSearchConfig(req *anthropic.MessageNewParams, config map[string]any) {
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
					allowedDomains := extractStringArray(domains)
					if len(allowedDomains) > 0 {
						webSearchTool.OfWebSearchTool20250305.AllowedDomains = allowedDomains
					}
				}
			}

			// Set blocked domains if specified
			if blockedDomainsVal, blockedExists := config["webSearchBlockedDomains"]; blockedExists {
				if domains, ok := blockedDomainsVal.([]interface{}); ok {
					blockedDomains := extractStringArray(domains)
					if len(blockedDomains) > 0 {
						webSearchTool.OfWebSearchTool20250305.BlockedDomains = blockedDomains
					}
				}
			}

			// Add the web search tool to the request
			req.Tools = append(req.Tools, webSearchTool)
		}
	}
}

// extractStringArray extracts string array from interface{} array
func extractStringArray(domains []interface{}) []string {
	var result []string
	for _, domain := range domains {
		if domainStr, ok := domain.(string); ok && domainStr != "" {
			result = append(result, domainStr)
		}
	}
	return result
}

// applyPassThroughConfig applies configuration parameters from the UI config
// This handles both common generation parameters and Anthropic-specific parameters
func applyPassThroughConfig(req *anthropic.MessageNewParams, config map[string]any) error {
	// Apply common generation parameters
	applyCommonPassThroughParams(req, config)

	// Apply Anthropic-specific parameters
	applyAnthropicSpecificParams(req, config)

	// Apply web search configuration
	applyWebSearchConfig(req, config)

	// Note: Code execution is handled in toAnthropicRequest by using Beta API
	// Regular API requests don't include code execution tools

	return nil
}

// toAnthropicBetaRequest translates [ai.ModelRequest] to a Beta API request for beta features
func toAnthropicBetaRequest(model string, i *ai.ModelRequest) (*anthropic.BetaMessageNewParams, error) {
	c, err := configFromRequest(i)
	if err != nil {
		return nil, err
	}

	// Apply common configuration
	finalModel, maxTokens, stopSequences := applyCommonConfig(c, model)

	// Start with minimum required data for Beta API
	req := anthropic.BetaMessageNewParams{
		Model:         finalModel,
		MaxTokens:     maxTokens,
		StopSequences: stopSequences,
	}

	// Apply Beta API specific configuration
	applyBetaAPIConfig(&req, c)

	// Process messages
	messages, sysBlocks, err := processBetaMessages(i.Messages)
	if err != nil {
		return nil, err
	}

	req.System = sysBlocks
	req.Messages = messages

	// Add code execution tool for Beta API
	betaTools := []anthropic.BetaToolUnionParam{
		{
			OfCodeExecutionTool20250825: &anthropic.BetaCodeExecutionTool20250825Param{},
		},
	}

	// Add regular tools converted to Beta format
	regularTools, err := toAnthropicBetaTools(i.Tools)
	if err != nil {
		return nil, err
	}
	betaTools = append(betaTools, regularTools...)

	req.Tools = betaTools

	return &req, nil
}

// processBetaMessages processes messages for Beta API
func processBetaMessages(messages []*ai.Message) ([]anthropic.BetaMessageParam, []anthropic.BetaTextBlockParam, error) {
	var msgParams []anthropic.BetaMessageParam
	var sysBlocks []anthropic.BetaTextBlockParam

	for _, message := range messages {
		if message.Role == ai.RoleSystem {
			// only text is supported for system messages
			sysBlocks = append(sysBlocks, anthropic.BetaTextBlockParam{Text: message.Text()})
		} else if len(message.Content) > 0 && message.Content[len(message.Content)-1].IsToolResponse() {
			// if the last message is a ToolResponse, the conversation must continue
			// and the ToolResponse message must be sent as a user
			parts, err := toAnthropicBetaParts(message.Content)
			if err != nil {
				return nil, nil, err
			}
			msgParams = append(msgParams, anthropic.NewBetaUserMessage(parts...))
		} else {
			parts, err := toAnthropicBetaParts(message.Content)
			if err != nil {
				return nil, nil, err
			}
			role, err := toAnthropicBetaRole(message.Role)
			if err != nil {
				return nil, nil, err
			}
			msgParams = append(msgParams, anthropic.BetaMessageParam{
				Role:    role,
				Content: parts,
			})
		}
	}

	return msgParams, sysBlocks, nil
}

// ============================================================================
// Tool and Schema Conversion Helper Functions
// ============================================================================

// toAnthropicBetaRole converts ai.Role to anthropic.BetaMessageParamRole
func toAnthropicBetaRole(role ai.Role) (anthropic.BetaMessageParamRole, error) {
	switch role {
	case ai.RoleUser:
		return anthropic.BetaMessageParamRoleUser, nil
	case ai.RoleModel:
		return anthropic.BetaMessageParamRoleAssistant, nil
	case ai.RoleTool:
		return anthropic.BetaMessageParamRoleAssistant, nil
	default:
		return "", fmt.Errorf("unknown role given: %q", role)
	}
}

// toAnthropicBetaTools translates [ai.ToolDefinition] to Beta API tools
func toAnthropicBetaTools(tools []*ai.ToolDefinition) ([]anthropic.BetaToolUnionParam, error) {
	resp := make([]anthropic.BetaToolUnionParam, 0)
	regex := regexp.MustCompile(toolNameRegex)

	for _, t := range tools {
		if t.Name == "" {
			return nil, fmt.Errorf("tool name is required")
		}
		if !regex.MatchString(t.Name) {
			return nil, fmt.Errorf("tool name must match regex: %s", toolNameRegex)
		}

		resp = append(resp, anthropic.BetaToolUnionParam{
			OfTool: &anthropic.BetaToolParam{
				Name:        t.Name,
				Description: anthropic.String(t.Description),
				InputSchema: toAnthropicBetaSchema[map[string]any](),
			},
		})
	}

	return resp, nil
}

// toAnthropicBetaSchema generates a JSON schema for Beta API
func toAnthropicBetaSchema[T any]() anthropic.BetaToolInputSchemaParam {
	reflector := jsonschema.Reflector{
		AllowAdditionalProperties: true,
		DoNotReference:            true,
	}
	var v T
	schema := reflector.Reflect(v)
	return anthropic.BetaToolInputSchemaParam{
		Properties: schema.Properties,
	}
}

// toAnthropicBetaParts translates [ai.Part] to Beta API content blocks
func toAnthropicBetaParts(parts []*ai.Part) ([]anthropic.BetaContentBlockParamUnion, error) {
	blocks := []anthropic.BetaContentBlockParamUnion{}

	for _, p := range parts {
		switch {
		case p.IsText():
			blocks = append(blocks, anthropic.NewBetaTextBlock(p.Text))
		case p.IsMedia():
			// Check if this is an HTTP URL that needs custom downloading
			if strings.HasPrefix(p.Text, "http://") || strings.HasPrefix(p.Text, "https://") {
				contentType, data, err := downloadImageFromURL(p.Text)
				if err != nil {
					return nil, fmt.Errorf("failed to download image from URL %s: %w", p.Text, err)
				}
				blocks = append(blocks, anthropic.NewBetaImageBlock(anthropic.BetaBase64ImageSourceParam{
					Data:      base64.StdEncoding.EncodeToString(data),
					MediaType: anthropic.BetaBase64ImageSourceMediaType(contentType),
				}))
			} else {
				// Use the original uri.Data for non-HTTP URLs (file://, data:, etc.)
				contentType, data, err := uri.Data(p)
				if err != nil {
					return nil, err
				}
				blocks = append(blocks, anthropic.NewBetaImageBlock(anthropic.BetaBase64ImageSourceParam{
					Data:      base64.StdEncoding.EncodeToString(data),
					MediaType: anthropic.BetaBase64ImageSourceMediaType(contentType),
				}))
			}
		case p.IsData():
			// Check if this is an HTTP URL that needs custom downloading
			if strings.HasPrefix(p.Text, "http://") || strings.HasPrefix(p.Text, "https://") {
				contentType, data, err := downloadImageFromURL(p.Text)
				if err != nil {
					return nil, fmt.Errorf("failed to download image from URL %s: %w", p.Text, err)
				}
				blocks = append(blocks, anthropic.NewBetaImageBlock(anthropic.BetaBase64ImageSourceParam{
					Data:      base64.StdEncoding.EncodeToString(data),
					MediaType: anthropic.BetaBase64ImageSourceMediaType(contentType),
				}))
			} else {
				// Use the original uri.Data for non-HTTP URLs (file://, data:, etc.)
				contentType, data, err := uri.Data(p)
				if err != nil {
					return nil, err
				}
				blocks = append(blocks, anthropic.NewBetaImageBlock(anthropic.BetaBase64ImageSourceParam{
					Data:      base64.RawStdEncoding.EncodeToString(data),
					MediaType: anthropic.BetaBase64ImageSourceMediaType(contentType),
				}))
			}
		case p.IsToolRequest():
			toolReq := p.ToolRequest
			blocks = append(blocks, anthropic.NewBetaToolUseBlock(toolReq.Ref, toolReq.Input, toolReq.Name))
		case p.IsToolResponse():
			toolResp := p.ToolResponse
			blocks = append(blocks, anthropic.NewBetaToolResultBlock(toolResp.Ref))
		default:
			return nil, errors.New("unknown part type in the request")
		}
	}

	return blocks, nil
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

// ============================================================================
// Response Conversion Functions
// ============================================================================

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

// ============================================================================
// Code Execution Helper Functions (Google AI Plugin Pattern)
// ============================================================================

// NewCodeExecutionResultPart creates a Part containing code execution results
// Following Google AI plugin pattern from gemini.go:800
func NewCodeExecutionResultPart(outcome string, output string) *ai.Part {
	return ai.NewCustomPart(map[string]any{
		"codeExecutionResult": map[string]any{
			"outcome": outcome,
			"output":  output,
		},
	})
}

// NewExecutableCodePart creates a Part containing executable code
// Following Google AI plugin pattern from gemini.go:810
func NewExecutableCodePart(language string, code string) *ai.Part {
	return ai.NewCustomPart(map[string]any{
		"executableCode": map[string]any{
			"language": language,
			"code":     code,
		},
	})
}

// CodeExecutionResult represents the result of a code execution
// Following Google AI plugin pattern from gemini.go:788
type CodeExecutionResult struct {
	Outcome string `json:"outcome"`
	Output  string `json:"output"`
}

// ExecutableCode represents executable code
// Following Google AI plugin pattern from gemini.go:794
type ExecutableCode struct {
	Language string `json:"language"`
	Code     string `json:"code"`
}

// ToCodeExecutionResult tries to convert an ai.Part to a CodeExecutionResult
// Following Google AI plugin pattern from gemini.go:821
func ToCodeExecutionResult(part *ai.Part) *CodeExecutionResult {
	if !part.IsCustom() {
		return nil
	}

	codeExec, ok := part.Custom["codeExecutionResult"]
	if !ok {
		return nil
	}

	result, ok := codeExec.(map[string]any)
	if !ok {
		return nil
	}

	outcome, _ := result["outcome"].(string)
	output, _ := result["output"].(string)

	return &CodeExecutionResult{
		Outcome: outcome,
		Output:  output,
	}
}

// ToExecutableCode tries to convert an ai.Part to an ExecutableCode
// Following Google AI plugin pattern from gemini.go:847
func ToExecutableCode(part *ai.Part) *ExecutableCode {
	if !part.IsCustom() {
		return nil
	}

	execCode, ok := part.Custom["executableCode"]
	if !ok {
		return nil
	}

	code, ok := execCode.(map[string]any)
	if !ok {
		return nil
	}

	language, _ := code["language"].(string)
	codeStr, _ := code["code"].(string)

	return &ExecutableCode{
		Language: language,
		Code:     codeStr,
	}
}

// HasCodeExecution checks if a message contains code execution results or executable code
// Following Google AI plugin pattern from gemini.go:872
func HasCodeExecution(msg *ai.Message) bool {
	return GetCodeExecutionResult(msg) != nil || GetExecutableCode(msg) != nil
}

// GetExecutableCode returns the first executable code from a message
// Following Google AI plugin pattern from gemini.go:878
func GetExecutableCode(msg *ai.Message) *ExecutableCode {
	for _, part := range msg.Content {
		if code := ToExecutableCode(part); code != nil {
			return code
		}
	}
	return nil
}

// ============================================================================
// Server Tool Helper Functions
// ============================================================================

// ServerToolUse represents a server-side tool usage
type ServerToolUse struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	Input any    `json:"input"`
	Type  string `json:"type"`
}

// NewServerToolUsePart creates a Part containing server tool use information
func NewServerToolUsePart(id, name, toolType string, input any) *ai.Part {
	return ai.NewCustomPart(map[string]any{
		"serverToolUse": map[string]any{
			"id":    id,
			"name":  name,
			"input": input,
			"type":  toolType,
		},
	})
}

// ToServerToolUse tries to convert an ai.Part to a ServerToolUse
func ToServerToolUse(part *ai.Part) *ServerToolUse {
	if !part.IsCustom() {
		return nil
	}

	serverTool, ok := part.Custom["serverToolUse"]
	if !ok {
		return nil
	}

	toolData, ok := serverTool.(map[string]any)
	if !ok {
		return nil
	}

	id, _ := toolData["id"].(string)
	name, _ := toolData["name"].(string)
	toolType, _ := toolData["type"].(string)
	input := toolData["input"]

	return &ServerToolUse{
		ID:    id,
		Name:  name,
		Input: input,
		Type:  toolType,
	}
}

// HasServerToolUse checks if a message contains server tool use
func HasServerToolUse(msg *ai.Message) bool {
	return GetServerToolUse(msg) != nil
}

// GetServerToolUse returns the first server tool use from a message
func GetServerToolUse(msg *ai.Message) *ServerToolUse {
	for _, part := range msg.Content {
		if serverTool := ToServerToolUse(part); serverTool != nil {
			return serverTool
		}
	}
	return nil
}

// GetCodeExecutionResult returns the first code execution result from a message
// Following Google AI plugin pattern from gemini.go:889
func GetCodeExecutionResult(msg *ai.Message) *CodeExecutionResult {
	for _, part := range msg.Content {
		if result := ToCodeExecutionResult(part); result != nil {
			return result
		}
	}
	return nil
}

// ============================================================================
// Beta API Response Parsing Helper Functions
// ============================================================================

// createExecutableCodePartFromToolUse extracts executable code from server_tool_use blocks
func createExecutableCodePartFromToolUse(part anthropic.BetaContentBlockUnion) *ai.Part {
	// Extract the command/code from the tool input
	var language, code string

	// Parse the input JSON
	var inputMap map[string]any
	if len(part.Input) > 0 {
		if err := json.Unmarshal(part.Input, &inputMap); err != nil {
			// If we can't parse the input, fall back to a text representation
			return ai.NewTextPart(fmt.Sprintf("Code execution: %s", part.Name))
		}
	}

	if part.Name == "bash_code_execution" {
		language = "bash"
		// Extract command from input
		if command, exists := inputMap["command"]; exists {
			if commandStr, ok := command.(string); ok {
				code = commandStr
			}
		}
	} else if part.Name == "text_editor_code_execution" {
		// For text editor, determine language based on the operation
		language = "text"
		// Extract the operation details from input
		if command, exists := inputMap["command"]; exists {
			if commandStr, ok := command.(string); ok {
				switch commandStr {
				case "create", "str_replace":
					if fileText, exists := inputMap["file_text"]; exists {
						if fileTextStr, ok := fileText.(string); ok {
							code = fileTextStr
							// Try to infer language from file extension
							if path, pathExists := inputMap["path"]; pathExists {
								if pathStr, ok := path.(string); ok {
									language = inferLanguageFromPath(pathStr)
								}
							}
						}
					}
				case "view":
					// For view operations, we don't have executable code
					return ai.NewTextPart(fmt.Sprintf("Viewing file: %v", inputMap["path"]))
				}
			}
		}
	}

	// If we couldn't extract proper code, fall back to a text representation
	if code == "" {
		return ai.NewTextPart(fmt.Sprintf("Code execution: %s", part.Name))
	}

	// Create the executable code part following Google AI plugin pattern
	return NewExecutableCodePart(language, code)
}

// createCodeExecutionResultPartFromToolResult extracts execution results from tool result blocks
func createCodeExecutionResultPartFromToolResult(part anthropic.BetaContentBlockUnion) *ai.Part {
	var outcome, output string

	// The content should contain the execution result details
	// We need to extract this from the part's content structure
	if part.Type == "bash_code_execution_tool_result" {
		// Extract bash execution results
		outcome, output = extractBashExecutionResult(part)
	} else if part.Type == "text_editor_code_execution_tool_result" {
		// Extract text editor execution results
		outcome, output = extractTextEditorExecutionResult(part)
	} else {
		// Handle unknown result types - this might be the issue
		// The actual result type might be different than expected
		outcome = "success"
		if part.Text != "" {
			output = part.Text
		} else {
			// Try to extract any meaningful information from the part
			if part.ID != "" {
				output = fmt.Sprintf("Execution completed (ID: %s, Type: %s)", part.ID, part.Type)
			} else {
				output = fmt.Sprintf("Execution completed (Type: %s)", part.Type)
			}
		}
	}

	// Create the code execution result part following Google AI plugin pattern
	return NewCodeExecutionResultPart(outcome, output)
}

// extractCodeExecutionResult extracts outcome and output from any code execution result
// This unified function handles both bash and text editor execution results
func extractCodeExecutionResult(part anthropic.BetaContentBlockUnion, operationType string) (outcome, output string) {
	// Default outcome
	outcome = "success"

	// Primary: Try to extract from the Text field
	if part.Text != "" {
		output = part.Text
		outcome = detectErrorFromText(part.Text)
		return outcome, output
	}

	// Fallback: Extract from content structure (stdout/stderr/return_code)
	if part.Content.Stdout != "" || part.Content.Stderr != "" {
		var outputParts []string

		if part.Content.Stdout != "" {
			outputParts = append(outputParts, part.Content.Stdout)
		}

		if part.Content.Stderr != "" {
			outputParts = append(outputParts, fmt.Sprintf("STDERR: %s", part.Content.Stderr))
			outcome = "error"
		}

		if len(outputParts) > 0 {
			output = strings.Join(outputParts, "\n")
		}

		// Check return code for error detection
		if part.Content.ReturnCode != 0 {
			outcome = "error"
			if output == "" {
				output = fmt.Sprintf("%s failed with exit code %d", operationType, part.Content.ReturnCode)
			}
		}

		if output != "" {
			return outcome, output
		}
	}

	// Final fallback: Generate descriptive message
	if part.ID != "" {
		output = fmt.Sprintf("%s completed (ID: %s)", operationType, part.ID)
	} else {
		output = fmt.Sprintf("%s completed", operationType)
	}

	return outcome, output
}

// detectErrorFromText analyzes text content for common error patterns
func detectErrorFromText(text string) string {
	lowerText := strings.ToLower(text)
	if strings.Contains(lowerText, "error") ||
		strings.Contains(lowerText, "failed") ||
		strings.Contains(lowerText, "exception") ||
		strings.Contains(lowerText, "traceback") ||
		strings.Contains(lowerText, "not found") {
		return "error"
	}
	return "success"
}

// extractBashExecutionResult extracts outcome and output from bash execution results
func extractBashExecutionResult(part anthropic.BetaContentBlockUnion) (outcome, output string) {
	return extractCodeExecutionResult(part, "Code execution")
}

// extractTextEditorExecutionResult extracts outcome and output from text editor execution results
func extractTextEditorExecutionResult(part anthropic.BetaContentBlockUnion) (outcome, output string) {
	return extractCodeExecutionResult(part, "File operation")
}

// inferLanguageFromPath attempts to infer the programming language from a file path
func inferLanguageFromPath(path string) string {
	// Extract file extension
	parts := strings.Split(path, ".")
	if len(parts) < 2 {
		return "text"
	}

	ext := strings.ToLower(parts[len(parts)-1])

	// Map common extensions to languages
	switch ext {
	case "py":
		return "python"
	case "js", "mjs":
		return "javascript"
	case "ts":
		return "typescript"
	case "go":
		return "go"
	case "java":
		return "java"
	case "cpp", "cc", "cxx":
		return "cpp"
	case "c":
		return "c"
	case "rs":
		return "rust"
	case "rb":
		return "ruby"
	case "php":
		return "php"
	case "sh", "bash":
		return "bash"
	case "sql":
		return "sql"
	case "html":
		return "html"
	case "css":
		return "css"
	case "json":
		return "json"
	case "yaml", "yml":
		return "yaml"
	case "xml":
		return "xml"
	case "md":
		return "markdown"
	default:
		return "text"
	}
}
