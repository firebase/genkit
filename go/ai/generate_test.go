// Copyright 2025 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"fmt"
	"math"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/internal/registry"
	test_utils "github.com/firebase/genkit/go/tests/utils"
	"github.com/google/go-cmp/cmp"
)

type StructuredResponse struct {
	Subject  string
	Location string
}

var r = registry.New()

func init() {
	// Set up default formats
	ConfigureFormats(r)
	// Register the generate action that Generate() function expects
	DefineGenerateAction(context.Background(), r)
}

// echoModel attributes
var (
	modelName = "echo"
	metadata  = ModelOptions{
		Label: modelName,
		Supports: &ModelSupports{
			Multiturn:   true,
			Tools:       true,
			SystemRole:  true,
			Media:       false,
			Constrained: ConstrainedSupportNone,
		},
		Versions: []string{"echo-001", "echo-002"},
		Stage:    ModelStageDeprecated,
	}

	echoModel = DefineModel(r, "test/"+modelName, &metadata, func(ctx context.Context, gr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
		if msc != nil {
			msc(ctx, &ModelResponseChunk{
				Content: []*Part{NewTextPart("stream!")},
			})
		}
		textResponse := ""
		for _, m := range gr.Messages {
			if m.Role == RoleUser {
				textResponse = m.Text()
			}
		}
		return &ModelResponse{
			Request: gr,
			Message: NewModelTextMessage(textResponse),
		}, nil
	})
)

// with tools
var gablorkenTool = DefineTool(r, "gablorken", "use when need to calculate a gablorken",
	func(ctx *ToolContext, input struct {
		Value float64
		Over  float64
	},
	) (float64, error) {
		return math.Pow(input.Value, input.Over), nil
	},
)

func TestStreamingChunksHaveRoleAndIndex(t *testing.T) {
	t.Parallel()

	ctx := context.Background()

	convertTempTool := DefineTool(r, "convertTemp", "converts temperature",
		func(ctx *ToolContext, input struct {
			From        string
			To          string
			Temperature float64
		}) (float64, error) {
			if input.From == "celsius" && input.To == "fahrenheit" {
				return input.Temperature*9/5 + 32, nil
			}
			return input.Temperature, nil
		},
	)

	toolModel := DefineModel(r, "test/toolModel", &metadata, func(ctx context.Context, gr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
		hasToolResponse := false
		for _, msg := range gr.Messages {
			if msg.Role == RoleTool {
				hasToolResponse = true
				break
			}
		}

		if hasToolResponse {
			if msc != nil {
				msc(ctx, &ModelResponseChunk{
					Content: []*Part{NewTextPart("20 degrees Celsius is 68 degrees Fahrenheit.")},
				})
			}
			return &ModelResponse{
				Request: gr,
				Message: NewModelTextMessage("20 degrees Celsius is 68 degrees Fahrenheit."),
			}, nil
		}

		if msc != nil {
			msc(ctx, &ModelResponseChunk{
				Content: []*Part{NewToolRequestPart(&ToolRequest{
					Name: "convertTemp",
					Input: map[string]any{
						"From":        "celsius",
						"To":          "fahrenheit",
						"Temperature": 20.0,
					},
					Ref: "0",
				})},
			})
		}
		return &ModelResponse{
			Request: gr,
			Message: &Message{
				Role: RoleModel,
				Content: []*Part{NewToolRequestPart(&ToolRequest{
					Name: "convertTemp",
					Input: map[string]any{
						"From":        "celsius",
						"To":          "fahrenheit",
						"Temperature": 20.0,
					},
					Ref: "0",
				})},
			},
		}, nil
	})

	var chunks []*ModelResponseChunk
	_, err := Generate(ctx, r,
		WithModel(toolModel),
		WithMessages(NewUserTextMessage("convert 20 c to f")),
		WithTools(convertTempTool),
		WithStreaming(func(ctx context.Context, chunk *ModelResponseChunk) error {
			chunks = append(chunks, chunk)
			return nil
		}),
	)
	if err != nil {
		t.Fatalf("Generate failed: %v", err)
	}

	if len(chunks) < 2 {
		t.Fatalf("Expected at least 2 chunks, got %d", len(chunks))
	}

	for i, chunk := range chunks {
		if chunk.Role == "" {
			t.Errorf("Chunk %d: Role is empty", i)
		}
		t.Logf("Chunk %d: Role=%s, Index=%d", i, chunk.Role, chunk.Index)
	}

	if chunks[0].Role != RoleModel {
		t.Errorf("Expected first chunk to have role 'model', got %s", chunks[0].Role)
	}
	if chunks[0].Index != 0 {
		t.Errorf("Expected first chunk to have index 0, got %d", chunks[0].Index)
	}

	toolChunkFound := false
	for _, chunk := range chunks {
		if chunk.Role == RoleTool {
			toolChunkFound = true
			if chunk.Index != 1 {
				t.Errorf("Expected tool chunk to have index 1, got %d", chunk.Index)
			}
		}
	}
	if !toolChunkFound {
		t.Error("Expected to find at least one tool chunk")
	}
}

func TestValidMessage(t *testing.T) {
	t.Parallel()

	t.Run("Valid message with text format", func(t *testing.T) {
		message := &Message{
			Content: []*Part{
				NewTextPart("Hello, World!"),
			},
		}
		outputSchema := &ModelOutputConfig{
			Format: OutputFormatText,
		}
		_, err := validTestMessage(message, outputSchema)
		if err != nil {
			t.Fatal(err)
		}
	})

	t.Run("Valid message with JSON format and matching schema", func(t *testing.T) {
		json := `{
			"name": "John",
			"age": 30,
			"address": {
				"street": "123 Main St",
				"city": "New York",
				"country": "USA"
			}
		}`
		message := &Message{
			Content: []*Part{
				NewTextPart(JSONMarkdown(json)),
			},
		}
		outputSchema := &ModelOutputConfig{
			Format: OutputFormatJSON,
			Schema: map[string]any{
				"type":     "object",
				"required": []string{"name", "age", "address"},
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
					"age":  map[string]any{"type": "integer"},
					"address": map[string]any{
						"type":     "object",
						"required": []string{"street", "city", "country"},
						"properties": map[string]any{
							"street":  map[string]any{"type": "string"},
							"city":    map[string]any{"type": "string"},
							"country": map[string]any{"type": "string"},
						},
					},
					"phone": map[string]any{"type": "string"},
				},
			},
		}
		message, err := validTestMessage(message, outputSchema)
		if err != nil {
			t.Fatal(err)
		}
		text := message.Text()
		if strings.TrimSpace(text) != strings.TrimSpace(json) {
			t.Fatalf("got %q, want %q", json, text)
		}
	})

	t.Run("Invalid message with JSON format and non-matching schema", func(t *testing.T) {
		message := &Message{
			Content: []*Part{
				NewTextPart(JSONMarkdown(`{"name": "John", "age": "30"}`)),
			},
		}
		outputSchema := &ModelOutputConfig{
			Format: OutputFormatJSON,
			Schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
					"age":  map[string]any{"type": "integer"},
				},
			},
		}
		_, err := validTestMessage(message, outputSchema)
		errorContains(t, err, "data did not match expected schema")
	})

	t.Run("Message with invalid JSON", func(t *testing.T) {
		message := &Message{
			Content: []*Part{
				NewTextPart(JSONMarkdown(`{"name": "John", "age": 30`)), // Missing trailing }.
			},
		}
		outputSchema := &ModelOutputConfig{
			Format: OutputFormatJSON,
		}
		_, err := validTestMessage(message, outputSchema)
		t.Log(err)
		errorContains(t, err, "not a valid JSON")
	})

	t.Run("No message", func(t *testing.T) {
		outputSchema := &ModelOutputConfig{
			Format: OutputFormatJSON,
		}
		_, err := validTestMessage(nil, outputSchema)
		errorContains(t, err, "message is empty")
	})

	t.Run("Empty message", func(t *testing.T) {
		message := &Message{}
		outputSchema := &ModelOutputConfig{
			Format: OutputFormatJSON,
		}
		_, err := validTestMessage(message, outputSchema)
		errorContains(t, err, "message has no content")
	})

	t.Run("Candidate contains unexpected field", func(t *testing.T) {
		message := &Message{
			Content: []*Part{
				NewTextPart(JSONMarkdown(`{"name": "John", "height": 190}`)),
			},
		}
		outputSchema := &ModelOutputConfig{
			Format: OutputFormatJSON,
			Schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
					"age":  map[string]any{"type": "integer"},
				},
				"additionalProperties": false,
			},
		}
		_, err := validTestMessage(message, outputSchema)
		errorContains(t, err, "data did not match expected schema")
	})

	t.Run("Invalid expected schema", func(t *testing.T) {
		message := &Message{
			Content: []*Part{
				NewTextPart(JSONMarkdown(`{"name": "John", "age": 30}`)),
			},
		}
		outputSchema := &ModelOutputConfig{
			Format: OutputFormatJSON,
			Schema: map[string]any{
				"type": "invalid",
			},
		}
		_, err := validTestMessage(message, outputSchema)
		errorContains(t, err, "failed to validate data against expected schema")
	})
}

func TestGenerate(t *testing.T) {
	JSON := "{\"subject\": \"bananas\", \"location\": \"tropics\"}"
	JSONmd := "```json" + JSON + "```"

	bananaModel := DefineModel(r, "test/banana", &metadata, func(ctx context.Context, gr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
		if msc != nil {
			msc(ctx, &ModelResponseChunk{
				Content: []*Part{NewTextPart("stream!")},
			})
		}

		return &ModelResponse{
			Request: gr,
			Message: NewModelTextMessage(JSONmd),
		}, nil
	})

	t.Run("constructs request", func(t *testing.T) {
		wantText := JSON
		wantStreamText := "stream!"
		wantRequest := &ModelRequest{
			Messages: []*Message{
				{
					Role: RoleSystem,
					Content: []*Part{
						NewTextPart("You are a helpful assistant."),
						{
							ContentType: "plain/text",
							Text:        "ignored (conformance message)",
							Metadata:    map[string]any{"purpose": string("output")},
						},
					},
				},
				NewUserTextMessage("How many bananas are there?"),
				NewModelTextMessage("There are at least 10 bananas."),
				{
					Role: RoleUser,
					Content: []*Part{
						NewTextPart("Where can they be found?"),
						{
							Text: "\n\nUse the following information " +
								"to complete your task:\n\n- [0]: Bananas are plentiful in the tropics.\n\n",
							Metadata: map[string]any{"purpose": "context"},
						},
					},
				},
			},
			Config: &GenerationCommonConfig{Temperature: 1},
			Docs:   []*Document{DocumentFromText("Bananas are plentiful in the tropics.", nil)},
			Output: &ModelOutputConfig{
				Format:      OutputFormatJSON,
				ContentType: "application/json",
			},
			Tools: []*ToolDefinition{
				{
					Description: "use when need to calculate a gablorken",
					InputSchema: map[string]any{
						"additionalProperties": bool(false),
						"properties": map[string]any{
							"Over":  map[string]any{"type": string("number")},
							"Value": map[string]any{"type": string("number")},
						},
						"required": []any{string("Value"), string("Over")},
						"type":     string("object"),
					},
					Name:         "gablorken",
					OutputSchema: map[string]any{"type": string("number")},
				},
			},
			ToolChoice: ToolChoiceAuto,
		}

		streamText := ""
		res, err := Generate(context.Background(), r,
			WithModel(bananaModel),
			WithSystem("You are a helpful assistant."),
			WithMessages(
				NewUserTextMessage("How many bananas are there?"),
				NewModelTextMessage("There are at least 10 bananas."),
			),
			WithPrompt("Where can they be found?"),
			WithConfig(&GenerationCommonConfig{
				Temperature: 1,
			}),
			WithDocs(DocumentFromText("Bananas are plentiful in the tropics.", nil)),
			WithOutputType(struct {
				Subject  string `json:"subject"`
				Location string `json:"location"`
			}{}),
			WithTools(gablorkenTool),
			WithToolChoice(ToolChoiceAuto),
			WithStreaming(func(ctx context.Context, grc *ModelResponseChunk) error {
				streamText += grc.Text()
				return nil
			}),
		)
		if err != nil {
			t.Fatal(err)
		}

		gotText := res.Text()
		if diff := cmp.Diff(gotText, wantText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(streamText, wantStreamText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(wantRequest, res.Request, test_utils.IgnoreNoisyParts([]string{
			"{*ai.ModelRequest}.Messages[0].Content[1].Text", "{*ai.ModelRequest}.Messages[0].Content[1].Metadata",
		})); diff != "" {
			t.Errorf("Request diff (+got -want):\n%s", diff)
		}
	})

	t.Run("handles tool interrupts", func(t *testing.T) {
		interruptTool := DefineTool(r, "interruptor", "always interrupts",
			func(ctx *ToolContext, input any) (any, error) {
				return nil, ctx.Interrupt(&InterruptOptions{
					Metadata: map[string]any{
						"reason": "test interrupt",
					},
				})
			},
		)

		info := &ModelOptions{
			Supports: &ModelSupports{
				Multiturn: true,
				Tools:     true,
			},
		}
		interruptModel := DefineModel(r, "test/interrupt", info,
			func(ctx context.Context, gr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
				return &ModelResponse{
					Request: gr,
					Message: &Message{
						Role: RoleModel,
						Content: []*Part{
							NewToolRequestPart(&ToolRequest{
								Name:  "interruptor",
								Input: nil,
							}),
						},
					},
				}, nil
			})

		res, err := Generate(context.Background(), r,
			WithModel(interruptModel),
			WithPrompt("trigger interrupt"),
			WithTools(interruptTool),
		)
		if err != nil {
			t.Fatal(err)
		}
		if res.FinishReason != "interrupted" {
			t.Errorf("expected finish reason 'interrupted', got %q", res.FinishReason)
		}
		if res.FinishMessage != "One or more tool calls resulted in interrupts." {
			t.Errorf("unexpected finish message: %q", res.FinishMessage)
		}

		if len(res.Message.Content) != 1 {
			t.Fatalf("expected 1 content part, got %d", len(res.Message.Content))
		}

		metadata := res.Message.Content[0].Metadata
		if metadata == nil {
			t.Fatal("expected metadata in content part")
		}

		interrupt, ok := metadata["interrupt"].(map[string]any)
		if !ok {
			t.Fatal("expected interrupt metadata")
		}

		reason, ok := interrupt["reason"].(string)
		if !ok || reason != "test interrupt" {
			t.Errorf("expected interrupt reason 'test interrupt', got %v", reason)
		}
	})

	t.Run("handles multiple parallel tool calls", func(t *testing.T) {
		roundCount := 0
		info := &ModelOptions{
			Supports: &ModelSupports{
				Multiturn: true,
				Tools:     true,
			},
		}
		parallelModel := DefineModel(r, "test/parallel", info,
			func(ctx context.Context, gr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
				roundCount++
				if roundCount == 1 {
					return &ModelResponse{
						Request: gr,
						Message: &Message{
							Role: RoleModel,
							Content: []*Part{
								NewToolRequestPart(&ToolRequest{
									Name:  "gablorken",
									Input: map[string]any{"Value": 2, "Over": 3},
								}),
								NewToolRequestPart(&ToolRequest{
									Name:  "gablorken",
									Input: map[string]any{"Value": 3, "Over": 2},
								}),
							},
						},
					}, nil
				}
				var sum float64
				for _, msg := range gr.Messages {
					if msg.Role == RoleTool {
						for _, part := range msg.Content {
							if part.ToolResponse != nil {
								sum += part.ToolResponse.Output.(float64)
							}
						}
					}
				}
				return &ModelResponse{
					Request: gr,
					Message: &Message{
						Role: RoleModel,
						Content: []*Part{
							NewTextPart(fmt.Sprintf("Final result: %d", int(sum))),
						},
					},
				}, nil
			})

		res, err := Generate(context.Background(), r,
			WithModel(parallelModel),
			WithPrompt("trigger parallel tools"),
			WithTools(gablorkenTool),
		)
		if err != nil {
			t.Fatal(err)
		}

		finalPart := res.Message.Content[0]
		if finalPart.Text != "Final result: 17" {
			t.Errorf("expected final result text to be 'Final result: 17', got %q", finalPart.Text)
		}
	})

	t.Run("handles multiple rounds of tool calls", func(t *testing.T) {
		roundCount := 0
		info := &ModelOptions{
			Supports: &ModelSupports{
				Multiturn: true,
				Tools:     true,
			},
		}
		multiRoundModel := DefineModel(r, "test/multiround", info,
			func(ctx context.Context, gr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
				roundCount++
				if roundCount == 1 {
					return &ModelResponse{
						Request: gr,
						Message: &Message{
							Role: RoleModel,
							Content: []*Part{
								NewToolRequestPart(&ToolRequest{
									Name:  "gablorken",
									Input: map[string]any{"Value": 2, "Over": 3},
								}),
							},
						},
					}, nil
				}
				if roundCount == 2 {
					return &ModelResponse{
						Request: gr,
						Message: &Message{
							Role: RoleModel,
							Content: []*Part{
								NewToolRequestPart(&ToolRequest{
									Name:  "gablorken",
									Input: map[string]any{"Value": 3, "Over": 2},
								}),
							},
						},
					}, nil
				}
				return &ModelResponse{
					Request: gr,
					Message: &Message{
						Role: RoleModel,
						Content: []*Part{
							NewTextPart("Final result"),
						},
					},
				}, nil
			})

		res, err := Generate(context.Background(), r,
			WithModel(multiRoundModel),
			WithPrompt("trigger multiple rounds"),
			WithTools(gablorkenTool),
			WithMaxTurns(2),
		)
		if err != nil {
			t.Fatal(err)
		}

		if roundCount != 3 {
			t.Errorf("expected 3 rounds, got %d", roundCount)
		}

		if res.Text() != "Final result" {
			t.Errorf("expected final message 'Final result', got %q", res.Text())
		}
	})

	t.Run("exceeds maximum turns", func(t *testing.T) {
		info := &ModelOptions{
			Supports: &ModelSupports{
				Multiturn: true,
				Tools:     true,
			},
		}
		infiniteModel := DefineModel(r, "test/infinite", info,
			func(ctx context.Context, gr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
				return &ModelResponse{
					Request: gr,
					Message: &Message{
						Role: RoleModel,
						Content: []*Part{
							NewToolRequestPart(&ToolRequest{
								Name:  "gablorken",
								Input: map[string]any{"Value": 2, "Over": 2},
							}),
						},
					},
				}, nil
			})

		_, err := Generate(context.Background(), r,
			WithModel(infiniteModel),
			WithPrompt("trigger infinite loop"),
			WithTools(gablorkenTool),
			WithMaxTurns(2),
		)

		if err == nil {
			t.Fatal("expected error for exceeding maximum turns")
		}
		if !strings.Contains(err.Error(), "exceeded maximum tool call iterations (2)") {
			t.Errorf("unexpected error message: %v", err)
		}
	})

	t.Run("applies middleware", func(t *testing.T) {
		middlewareCalled := false
		testMiddleware := func(next ModelFunc) ModelFunc {
			return func(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
				middlewareCalled = true
				req.Messages = append(req.Messages, NewUserTextMessage("middleware was here"))
				return next(ctx, req, cb)
			}
		}

		res, err := Generate(context.Background(), r,
			WithModel(echoModel),
			WithPrompt("test middleware"),
			WithMiddleware(testMiddleware),
		)
		if err != nil {
			t.Fatal(err)
		}

		if !middlewareCalled {
			t.Error("middleware was not called")
		}

		expectedText := "middleware was here"
		if res.Text() != expectedText {
			t.Errorf("got text %q, want %q", res.Text(), expectedText)
		}
	})

	t.Run("registers dynamic tools", func(t *testing.T) {
		// Create a tool that is NOT registered in the global registry
		dynamicTool := NewTool("dynamicTestTool", "a tool that is dynamically registered",
			func(ctx *ToolContext, input struct {
				Message string
			},
			) (string, error) {
				return "Dynamic: " + input.Message, nil
			},
		)

		// Verify the tool is not in the global registry
		if LookupTool(r, "dynamicTestTool") != nil {
			t.Fatal("dynamicTestTool should not be registered in global registry")
		}

		// Create a model that will call the dynamic tool then provide a final response
		roundCount := 0
		info := &ModelOptions{
			Supports: &ModelSupports{
				Multiturn: true,
				Tools:     true,
			},
		}
		toolCallModel := DefineModel(r, "test/toolcall", info,
			func(ctx context.Context, gr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
				roundCount++
				if roundCount == 1 {
					// First response: call the dynamic tool
					return &ModelResponse{
						Request: gr,
						Message: &Message{
							Role: RoleModel,
							Content: []*Part{
								NewToolRequestPart(&ToolRequest{
									Name:  "dynamicTestTool",
									Input: map[string]any{"Message": "Hello from dynamic tool"},
								}),
							},
						},
					}, nil
				}
				// Second response: provide final answer based on tool response
				var toolResult string
				for _, msg := range gr.Messages {
					if msg.Role == RoleTool {
						for _, part := range msg.Content {
							if part.ToolResponse != nil {
								toolResult = part.ToolResponse.Output.(string)
							}
						}
					}
				}
				return &ModelResponse{
					Request: gr,
					Message: &Message{
						Role: RoleModel,
						Content: []*Part{
							NewTextPart(toolResult),
						},
					},
				}, nil
			})

		// Use Generate with the dynamic tool - this should trigger the dynamic registration
		res, err := Generate(context.Background(), r,
			WithModel(toolCallModel),
			WithPrompt("call the dynamic tool"),
			WithTools(dynamicTool),
		)
		if err != nil {
			t.Fatal(err)
		}

		// The tool should have been called and returned a response
		expectedText := "Dynamic: Hello from dynamic tool"
		if res.Text() != expectedText {
			t.Errorf("expected text %q, got %q", expectedText, res.Text())
		}

		// Verify two rounds were executed: tool call + final response
		if roundCount != 2 {
			t.Errorf("expected 2 rounds, got %d", roundCount)
		}

		// Verify the tool is still not in the global registry (it was registered in a child)
		if LookupTool(r, "dynamicTestTool") != nil {
			t.Error("dynamicTestTool should not be registered in global registry after generation")
		}
	})

	t.Run("handles duplicate dynamic tools", func(t *testing.T) {
		// Create two tools with the same name
		dynamicTool1 := NewTool("duplicateTool", "first tool",
			func(ctx *ToolContext, input any) (string, error) {
				return "tool1", nil
			},
		)
		dynamicTool2 := NewTool("duplicateTool", "second tool",
			func(ctx *ToolContext, input any) (string, error) {
				return "tool2", nil
			},
		)

		// Using both tools should result in an error
		_, err := Generate(context.Background(), r,
			WithModel(echoModel),
			WithPrompt("test duplicate tools"),
			WithTools(dynamicTool1, dynamicTool2),
		)

		if err == nil {
			t.Fatal("expected error for duplicate tool names")
		}
		if !strings.Contains(err.Error(), "duplicate tool \"duplicateTool\"") {
			t.Errorf("unexpected error message: %v", err)
		}
	})
}

func TestModelVersion(t *testing.T) {
	t.Run("valid version", func(t *testing.T) {
		_, err := Generate(context.Background(), r,
			WithModel(echoModel),
			WithConfig(&GenerationCommonConfig{
				Temperature: 1,
				Version:     "echo-001",
			}),
			WithPrompt("tell a joke about batman"))
		if err != nil {
			t.Errorf("model version should be valid")
		}
	})
	t.Run("invalid version", func(t *testing.T) {
		_, err := Generate(context.Background(), r,
			WithModel(echoModel),
			WithConfig(&GenerationCommonConfig{
				Temperature: 1,
				Version:     "echo-im-not-a-version",
			}),
			WithPrompt("tell a joke about batman"))
		if err == nil {
			t.Errorf("model version should be invalid: %v", err)
		}
	})
}

func TestLookupModel(t *testing.T) {
	t.Run("should return model", func(t *testing.T) {
		if LookupModel(r, "test/"+modelName) == nil {
			t.Errorf("LookupModel did not return model")
		}
	})
	t.Run("should return nil", func(t *testing.T) {
		if LookupModel(r, "foo/bar") != nil {
			t.Errorf("LookupModel did not return nil")
		}
	})
}

func JSONMarkdown(text string) string {
	return "```json\n" + text + "\n```"
}

func errorContains(t *testing.T, err error, want string) {
	t.Helper()
	if err == nil {
		t.Error("got nil, want error")
	} else if !strings.Contains(err.Error(), want) {
		t.Errorf("got error message %q, want it to contain %q", err, want)
	}
}

func validTestMessage(m *Message, output *ModelOutputConfig) (*Message, error) {
	resolvedFormat, err := resolveFormat(r, output.Schema, output.Format)
	if err != nil {
		return nil, err
	}

	handler, err := resolvedFormat.Handler(output.Schema)
	if err != nil {
		return nil, err
	}

	return handler.ParseMessage(m)
}

func TestToolInterruptsAndResume(t *testing.T) {
	conditionalTool := DefineTool(r, "conditional", "tool that may interrupt based on input",
		func(ctx *ToolContext, input struct {
			Value     string
			Interrupt bool
		},
		) (string, error) {
			if input.Interrupt {
				return "", ctx.Interrupt(&InterruptOptions{
					Metadata: map[string]any{
						"reason":      "user_intervention_required",
						"value":       input.Value,
						"interrupted": true,
					},
				})
			}
			return fmt.Sprintf("processed: %s", input.Value), nil
		},
	)

	resumableTool := DefineTool(r, "resumable", "tool that can be resumed",
		func(ctx *ToolContext, input struct {
			Action string
			Data   string
		},
		) (string, error) {
			if ctx.Resumed != nil {
				resumedData, ok := ctx.Resumed["data"].(string)
				if ok {
					return fmt.Sprintf("resumed with: %s, original: %s", resumedData, input.Data), nil
				}
				return fmt.Sprintf("resumed: %s", input.Data), nil
			}
			return fmt.Sprintf("first run: %s", input.Data), nil
		},
	)

	info := &ModelOptions{
		Supports: &ModelSupports{
			Multiturn: true,
			Tools:     true,
		},
	}

	toolModel := DefineModel(r, "test/toolmodel", info,
		func(ctx context.Context, mr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
			return &ModelResponse{
				Request: mr,
				Message: &Message{
					Role: RoleModel,
					Content: []*Part{
						NewTextPart("I need to use some tools."),
						NewToolRequestPart(&ToolRequest{
							Name: "conditional",
							Ref:  "tool1",
							Input: map[string]any{
								"Value":     "test_data",
								"Interrupt": true,
							},
						}),
						NewToolRequestPart(&ToolRequest{
							Name: "resumable",
							Ref:  "tool2",
							Input: map[string]any{
								"Action": "process",
								"Data":   "initial_data",
							},
						}),
					},
				},
			}, nil
		})

	t.Run("basic interrupt flow", func(t *testing.T) {
		res, err := Generate(context.Background(), r,
			WithModel(toolModel),
			WithPrompt("use tools"),
			WithTools(conditionalTool, resumableTool),
		)
		if err != nil {
			t.Fatal(err)
		}

		if res.FinishReason != "interrupted" {
			t.Errorf("expected finish reason 'interrupted', got %q", res.FinishReason)
		}

		if len(res.Message.Content) != 3 {
			t.Fatalf("expected 3 content parts, got %d", len(res.Message.Content))
		}

		interruptedPart := res.Message.Content[1]
		if !interruptedPart.IsToolRequest() {
			t.Fatal("expected second part to be a tool request")
		}

		interruptMeta, ok := interruptedPart.Metadata["interrupt"].(map[string]any)
		if !ok {
			t.Fatal("expected interrupt metadata in tool request")
		}

		if reason, ok := interruptMeta["reason"].(string); !ok || reason != "user_intervention_required" {
			t.Errorf("expected interrupt reason 'user_intervention_required', got %v", reason)
		}
	})

	t.Run("tool.Respond functionality", func(t *testing.T) {
		res, err := Generate(context.Background(), r,
			WithModel(toolModel),
			WithPrompt("use tools"),
			WithTools(conditionalTool, resumableTool),
		)
		if err != nil {
			t.Fatal(err)
		}

		interruptedPart := res.Message.Content[1]

		responsePart := conditionalTool.Respond(interruptedPart, "manual_response_data", &RespondOptions{
			Metadata: map[string]any{
				"manual": true,
				"source": "user",
			},
		})

		if !responsePart.IsToolResponse() {
			t.Fatal("expected response part to be a tool response")
		}

		if responsePart.ToolResponse.Name != "conditional" {
			t.Errorf("expected tool response name 'conditional', got %q", responsePart.ToolResponse.Name)
		}

		if responsePart.ToolResponse.Ref != "tool1" {
			t.Errorf("expected tool response ref 'tool1', got %q", responsePart.ToolResponse.Ref)
		}

		if responsePart.ToolResponse.Output != "manual_response_data" {
			t.Errorf("expected output 'manual_response_data', got %v", responsePart.ToolResponse.Output)
		}

		interruptResponseMeta, ok := responsePart.Metadata["interruptResponse"].(map[string]any)
		if !ok {
			t.Fatal("expected interruptResponse metadata")
		}

		if manual, ok := interruptResponseMeta["manual"].(bool); !ok || !manual {
			t.Errorf("expected manual metadata to be true")
		}
	})

	t.Run("tool.Restart functionality", func(t *testing.T) {
		res, err := Generate(context.Background(), r,
			WithModel(toolModel),
			WithPrompt("use tools"),
			WithTools(conditionalTool, resumableTool),
		)
		if err != nil {
			t.Fatal(err)
		}

		interruptedPart := res.Message.Content[1]

		restartPart := conditionalTool.Restart(interruptedPart, &RestartOptions{
			ReplaceInput: map[string]any{
				"Value":     "new_test_data",
				"Interrupt": false,
			},
			ResumedMetadata: map[string]any{
				"data":   "resumed_data",
				"source": "restart",
			},
		})

		if !restartPart.IsToolRequest() {
			t.Fatal("expected restart part to be a tool request")
		}

		if restartPart.ToolRequest.Name != "conditional" {
			t.Errorf("expected tool request name 'conditional', got %q", restartPart.ToolRequest.Name)
		}

		newInput, ok := restartPart.ToolRequest.Input.(map[string]any)
		if !ok {
			t.Fatal("expected input to be map[string]any")
		}

		if newInput["Value"] != "new_test_data" {
			t.Errorf("expected new input value 'new_test_data', got %v", newInput["Value"])
		}

		if newInput["Interrupt"] != false {
			t.Errorf("expected interrupt to be false, got %v", newInput["Interrupt"])
		}

		if _, hasInterrupt := restartPart.Metadata["interrupt"]; hasInterrupt {
			t.Error("expected interrupt metadata to be removed")
		}

		resumedMeta, ok := restartPart.Metadata["resumed"].(map[string]any)
		if !ok {
			t.Fatal("expected resumed metadata")
		}

		if resumedMeta["data"] != "resumed_data" {
			t.Errorf("expected resumed data 'resumed_data', got %v", resumedMeta["data"])
		}
	})

	t.Run("resume with respond directive", func(t *testing.T) {
		res, err := Generate(context.Background(), r,
			WithModel(toolModel),
			WithPrompt("use tools"),
			WithTools(conditionalTool, resumableTool),
		)
		if err != nil {
			t.Fatal(err)
		}

		interruptedPart := res.Message.Content[1]
		responsePart := conditionalTool.Respond(interruptedPart, "user_provided_response", nil)

		history := res.History()
		resumeRes, err := Generate(context.Background(), r,
			WithModel(NewModelRef("test/echo", nil)),
			WithMessages(history...),
			WithTools(conditionalTool, resumableTool),
			WithToolResponses(responsePart),
		)
		if err != nil {
			t.Fatal(err)
		}

		if resumeRes.FinishReason == "interrupted" {
			t.Error("expected generation to not be interrupted after responding")
		}
	})

	t.Run("resume with restart directive", func(t *testing.T) {
		res, err := Generate(context.Background(), r,
			WithModel(toolModel),
			WithPrompt("use tools"),
			WithTools(conditionalTool, resumableTool),
		)
		if err != nil {
			t.Fatal(err)
		}

		interruptedPart := res.Message.Content[1]
		restartPart := conditionalTool.Restart(interruptedPart, &RestartOptions{
			ReplaceInput: map[string]any{
				"Value":     "restarted_data",
				"Interrupt": false,
			},
			ResumedMetadata: map[string]any{
				"data": "restart_context",
			},
		})

		history := res.History()
		resumeRes, err := Generate(context.Background(), r,
			WithModel(NewModelRef("test/echo", nil)),
			WithMessages(history...),
			WithTools(conditionalTool, resumableTool),
			WithToolRestarts(restartPart),
		)
		if err != nil {
			t.Fatal(err)
		}

		if resumeRes.FinishReason == "interrupted" {
			t.Error("expected generation to not be interrupted after restarting")
		}
	})
}

func TestResourceProcessing(t *testing.T) {
	r := registry.New()

	// Create test resources using DefineResource
	DefineResource(r, "test-file", &ResourceOptions{
		URI:         "file:///test.txt",
		Description: "Test file resource",
	}, func(ctx context.Context, input *ResourceInput) (*ResourceOutput, error) {
		return &ResourceOutput{Content: []*Part{NewTextPart("FILE CONTENT")}}, nil
	})

	DefineResource(r, "test-api", &ResourceOptions{
		URI:         "api://data/123",
		Description: "Test API resource",
	}, func(ctx context.Context, input *ResourceInput) (*ResourceOutput, error) {
		return &ResourceOutput{Content: []*Part{NewTextPart("API DATA")}}, nil
	})

	// Test message with resources
	messages := []*Message{
		NewUserMessage(
			NewTextPart("Read this:"),
			NewResourcePart("file:///test.txt"),
			NewTextPart("And this:"),
			NewResourcePart("api://data/123"),
			NewTextPart("Done."),
		),
	}

	// Process resources
	processed, err := processResources(context.Background(), r, messages)
	if err != nil {
		t.Fatalf("resource processing failed: %v", err)
	}

	// Verify content
	content := processed[0].Content
	expected := []string{"Read this:", "FILE CONTENT", "And this:", "API DATA", "Done."}

	if len(content) != len(expected) {
		t.Fatalf("expected %d parts, got %d", len(expected), len(content))
	}

	for i, want := range expected {
		if content[i].Text != want {
			t.Fatalf("part %d: got %q, want %q", i, content[i].Text, want)
		}
	}
}

func TestResourceProcessingError(t *testing.T) {
	r := registry.New()

	// No resources registered
	messages := []*Message{
		NewUserMessage(NewResourcePart("missing://resource")),
	}

	_, err := processResources(context.Background(), r, messages)
	if err == nil {
		t.Fatal("expected error when no resources available")
	}

	if !strings.Contains(err.Error(), "no resource found for URI") {
		t.Fatalf("wrong error: %v", err)
	}
}
