// Copyright 2026 Google LLC
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

package openai_test

import (
	"context"
	"encoding/base64"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	oai "github.com/firebase/genkit/go/plugins/openai"
	openai "github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/responses"
	"github.com/openai/openai-go/v3/shared"
)

func TestOpenAILive(t *testing.T) {
	if _, ok := requireEnv("OPENAI_API_KEY"); !ok {
		t.Skip("OPENAI_API_KEY not found in the environment")
	}

	ctx := context.Background()
	g := genkit.Init(ctx, genkit.WithPlugins(&oai.OpenAI{}))

	t.Run("model version ok", func(t *testing.T) {
		m := oai.Model(g, "gpt-4o")
		resp, err := genkit.Generate(ctx, g,
			ai.WithConfig(&responses.ResponseNewParams{
				Temperature:     openai.Float(1),
				MaxOutputTokens: openai.Int(1024),
			}),
			ai.WithModel(m),
			ai.WithSystem("talk to me like an evil pirate and say \"Arr\" several times but be very short"),
			ai.WithMessages(ai.NewUserMessage(ai.NewTextPart("I'm a fish"))),
		)
		if err != nil {
			t.Fatal(err)
		}

		if !strings.Contains(resp.Text(), "Arr") {
			t.Fatalf("not a pirate:%s", resp.Text())
		}
	})

	t.Run("model version not ok", func(t *testing.T) {
		m := oai.Model(g, "non-existent-model")
		_, err := genkit.Generate(ctx, g,
			ai.WithConfig(&responses.ResponseNewParams{
				Temperature:     openai.Float(1),
				MaxOutputTokens: openai.Int(1024),
			}),
			ai.WithModel(m),
		)
		if err == nil {
			t.Fatal("should have failed due wrong model version")
		}
	})

	t.Run("media content", func(t *testing.T) {
		i, err := fetchImgAsBase64()
		if err != nil {
			t.Fatal(err)
		}
		m := oai.Model(g, "gpt-4o")
		resp, err := genkit.Generate(ctx, g,
			ai.WithSystem("You are a professional image detective that talks like an evil pirate that loves animals, your task is to tell the name of the animal in the image but be very short"),
			ai.WithModel(m),
			ai.WithConfig(&responses.ResponseNewParams{
				Temperature:     openai.Float(1),
				MaxOutputTokens: openai.Int(1024),
			}),
			ai.WithMessages(
				ai.NewUserMessage(
					ai.NewTextPart("do you know which animal is in the image?"),
					ai.NewMediaPart("", "data:image/jpeg;base64,"+i))))
		if err != nil {
			t.Fatal(err)
		}
		if !strings.Contains(strings.ToLower(resp.Text()), "cat") {
			t.Fatalf("want: cat, got: %s", resp.Text())
		}
	})

	t.Run("media content stream", func(t *testing.T) {
		i, err := fetchImgAsBase64()
		if err != nil {
			t.Fatal(err)
		}
		out := ""
		m := oai.Model(g, "gpt-4o")
		resp, err := genkit.Generate(ctx, g,
			ai.WithSystem("You are a professional image detective that talks like an evil pirate that loves animals, your task is to tell the name of the animal in the image but be very short"),
			ai.WithModel(m),
			ai.WithConfig(&responses.ResponseNewParams{
				Temperature:     openai.Float(1),
				MaxOutputTokens: openai.Int(1024),
			}),
			ai.WithStreaming(func(ctx context.Context, c *ai.ModelResponseChunk) error {
				out += c.Content[0].Text
				return nil
			}),
			ai.WithMessages(
				ai.NewUserMessage(
					ai.NewTextPart("do you know which animal is in the image?"),
					ai.NewMediaPart("", "data:image/jpeg;base64,"+i))))
		if err != nil {
			t.Fatal(err)
		}
		if out != resp.Text() {
			t.Fatalf("want: %s, got: %s", resp.Text(), out)
		}
		if !strings.Contains(strings.ToLower(resp.Text()), "cat") {
			t.Fatalf("want: cat, got: %s", resp.Text())
		}
	})

	t.Run("media content stream with thinking", func(t *testing.T) {
		i, err := fetchImgAsBase64()
		if err != nil {
			t.Fatal(err)
		}
		out := ""
		m := oai.Model(g, "gpt-5")
		resp, err := genkit.Generate(ctx, g,
			ai.WithSystem(`You are a professional image detective that
				talks like an evil pirate that loves animals, your task is to tell the name
				of the animal in the image but be very short`),
			ai.WithModel(m),
			ai.WithConfig(&responses.ResponseNewParams{
				Reasoning: shared.ReasoningParam{
					Effort: shared.ReasoningEffortMedium,
				},
			}),
			ai.WithStreaming(func(ctx context.Context, c *ai.ModelResponseChunk) error {
				for _, p := range c.Content {
					if p.IsText() {
						out += p.Text
					}
				}
				return nil
			}),
			ai.WithMessages(
				ai.NewUserMessage(
					ai.NewTextPart("do you know which animal is in the image?"),
					ai.NewMediaPart("", "data:image/jpeg;base64,"+i))))
		if err != nil {
			t.Fatal(err)
		}

		if out != resp.Text() {
			t.Fatalf("want: %s, got: %s", resp.Text(), out)
		}
		if !strings.Contains(strings.ToLower(resp.Text()), "cat") {
			t.Fatalf("want: cat, got: %s", resp.Text())
		}
		// OpenAI does not return reasoning text, so we check usage.
		if resp.Usage.ThoughtsTokens == 0 {
			t.Log("No reasoning tokens found in usage (expected for reasoning models)")
		}
	})

	t.Run("tools", func(t *testing.T) {
		m := oai.Model(g, "gpt-5")
		myJokeTool := genkit.DefineTool(
			g,
			"myJoke",
			"When the user asks for a joke, this tool must be used to generate a joke, try to come up with a joke that uses the output of the tool",
			func(ctx *ai.ToolContext, input *any) (string, error) {
				return "why did the chicken cross the road?", nil
			},
		)
		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&responses.ResponseNewParams{
				Temperature:     openai.Float(1),
				MaxOutputTokens: openai.Int(1024),
			}),
			ai.WithPrompt("tell me a joke"),
			ai.WithTools(myJokeTool))
		if err != nil {
			t.Fatal(err)
		}

		if len(resp.Text()) == 0 {
			t.Fatal("expected a response but nothing was returned")
		}
	})

	t.Run("tools with schema", func(t *testing.T) {
		m := oai.Model(g, "gpt-4o")

		type WeatherInput struct {
			Location string `json:"location"`
		}

		weatherTool := genkit.DefineTool(
			g,
			"weather",
			"Returns the weather for the given location",
			func(ctx *ai.ToolContext, input *WeatherInput) (string, error) {
				return "sunny", nil
			},
		)

		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&responses.ResponseNewParams{
				Temperature:     openai.Float(1),
				MaxOutputTokens: openai.Int(1024),
			}),
			ai.WithPrompt("what is the weather in San Francisco?"),
			ai.WithTools(weatherTool))
		if err != nil {
			t.Fatal(err)
		}

		if len(resp.Text()) == 0 {
			t.Fatal("expected a response but nothing was returned")
		}
	})

	t.Run("streaming", func(t *testing.T) {
		m := oai.Model(g, "gpt-4o")
		out := ""

		final, err := genkit.Generate(ctx, g,
			ai.WithPrompt("Tell me a short story about a frog and a princess"),
			ai.WithConfig(&responses.ResponseNewParams{
				Temperature:     openai.Float(1),
				MaxOutputTokens: openai.Int(1024),
			}),
			ai.WithModel(m),
			ai.WithStreaming(func(ctx context.Context, c *ai.ModelResponseChunk) error {
				out += c.Content[0].Text
				return nil
			}),
		)
		if err != nil {
			t.Fatal(err)
		}

		out2 := ""
		for _, p := range final.Message.Content {
			out2 += p.Text
		}

		if out != out2 {
			t.Fatalf("streaming and final should contain the same text.\nstreaming: %s\nfinal:%s\n", out, out2)
		}
		if final.Usage.InputTokens == 0 || final.Usage.OutputTokens == 0 {
			t.Fatalf("empty usage stats: %#v", *final.Usage)
		}
	})

	t.Run("streaming with thinking", func(t *testing.T) {
		m := oai.Model(g, "gpt-5.2")
		out := ""

		final, err := genkit.Generate(ctx, g,
			ai.WithPrompt("Tell me a short story about a frog and a princess"),
			ai.WithConfig(&responses.ResponseNewParams{
				Reasoning: shared.ReasoningParam{
					Effort: shared.ReasoningEffortHigh,
				},
			}),
			ai.WithModel(m),
			ai.WithStreaming(func(ctx context.Context, c *ai.ModelResponseChunk) error {
				for _, p := range c.Content {
					if p.IsText() {
						out += p.Text
					}
				}
				return nil
			}),
		)
		if err != nil {
			t.Fatal(err)
		}

		out2 := ""
		for _, p := range final.Message.Content {
			if p.IsText() {
				out2 += p.Text
			}
		}
		if out != out2 {
			t.Fatalf("streaming and final should contain the same text.\n\nstreaming: %s\n\nfinal: %s\n\n", out, out2)
		}

		if final.Usage.ThoughtsTokens > 0 {
			t.Logf("Reasoning tokens: %d", final.Usage.ThoughtsTokens)
		} else {
			// This might happen if the model decides not to reason much or if stats are missing.
			t.Log("No reasoning tokens reported.")
		}
	})

	t.Run("tools streaming", func(t *testing.T) {
		m := oai.Model(g, "gpt-4o")
		out := ""

		myStoryTool := genkit.DefineTool(
			g,
			"myStory",
			"When the user asks for a story, create a story about a frog and a fox that are good friends",
			func(ctx *ai.ToolContext, input *any) (string, error) {
				return "the fox is named Goph and the frog is called Fred", nil
			},
		)

		final, err := genkit.Generate(ctx, g,
			ai.WithPrompt("Tell me a short story about a frog and a fox, do no mention anything else, only the short story"),
			ai.WithModel(m),
			ai.WithConfig(&responses.ResponseNewParams{
				Temperature:     openai.Float(1),
				MaxOutputTokens: openai.Int(1024),
			}),
			ai.WithTools(myStoryTool),
			ai.WithStreaming(func(ctx context.Context, c *ai.ModelResponseChunk) error {
				out += c.Content[0].Text
				return nil
			}),
		)
		if err != nil {
			t.Fatal(err)
		}

		out2 := ""
		for _, p := range final.Message.Content {
			if p.IsText() {
				out2 += p.Text
			}
		}

		if out != out2 {
			t.Fatalf("streaming and final should contain the same text\n\nstreaming: %s\n\nfinal: %s\n\n", out, out2)
		}
		if final.Usage.InputTokens == 0 || final.Usage.OutputTokens == 0 {
			t.Fatalf("empty usage stats: %#v", *final.Usage)
		}
	})

	t.Run("tools streaming with constrained gen", func(t *testing.T) {
		t.Skip("skipped until constrained gen is implemented")
	})

	t.Run("built-in tools", func(t *testing.T) {
		m := oai.Model(g, "gpt-4o")

		// define a built-in web search tool configuration
		webSearchTool := responses.ToolParamOfWebSearch(responses.WebSearchToolTypeWebSearch)

		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&responses.ResponseNewParams{
				Temperature:     openai.Float(1),
				MaxOutputTokens: openai.Int(1024),
				// Add built-in tool via config
				Tools: []responses.ToolUnionParam{webSearchTool},
			}),
			ai.WithPrompt("What's the current weather in SFO?"),
		)
		if err != nil {
			t.Fatal(err)
		}

		if len(resp.Text()) == 0 {
			t.Fatal("expected a response but nothing was returned")
		}

		fmt.Printf("tool requests: %#v\n", resp.ToolRequests())

		t.Logf("Response: %s", resp.Text())
	})

	t.Run("mixed tools", func(t *testing.T) {
		m := oai.Model(g, "gpt-4o")

		gablorkenDefinitionTool := genkit.DefineTool(
			g,
			"gablorkenDefinitionTool",
			"Custom tool that must be used when the user asks for the definition of a gablorken",
			func(ctx *ai.ToolContext, input *any) (string, error) {
				return "A gablorken is a interstellar currency for the Andromeda Galaxy. It is equivalent to 0.4 USD per Gablorken (GAB)", nil
			},
		)

		// define a built-in web search tool configuration
		webSearchTool := responses.ToolParamOfWebSearch(responses.WebSearchToolTypeWebSearch)

		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&responses.ResponseNewParams{
				Temperature:       openai.Float(1),
				MaxOutputTokens:   openai.Int(1024),
				ParallelToolCalls: openai.Bool(true),
				// Add built-in tool via config
				Tools: []responses.ToolUnionParam{webSearchTool},
			}),
			ai.WithPrompt("I'd would like to ask you two things: What's the current weather in SFO? What's the meaning of gablorken?"),
			ai.WithTools(gablorkenDefinitionTool),
		)
		if err != nil {
			t.Fatal(err)
		}

		if len(resp.Text()) == 0 {
			t.Fatal("expected a response but nothing was returned")
		}

		fmt.Printf("tool requests: %#v\n", resp.ToolRequests())

		t.Logf("Response: %s", resp.Text())
	})
}

func fetchImgAsBase64() (string, error) {
	// CC0 license image
	imgURL := "https://pd.w.org/2025/07/896686fbbcd9990c9.84605288-2048x1365.jpg"
	resp, err := http.Get(imgURL)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", err
	}

	imageBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	base64string := base64.StdEncoding.EncodeToString(imageBytes)
	return base64string, nil
}

func requireEnv(key string) (string, bool) {
	value, ok := os.LookupEnv(key)
	if !ok || value == "" {
		return "", false
	}

	return value, true
}
