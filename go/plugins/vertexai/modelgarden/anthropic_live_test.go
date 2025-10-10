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

package modelgarden_test

import (
	"context"
	"encoding/base64"
	"flag"
	"io"
	"net/http"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/vertexai/modelgarden"
)

var (
	provider  = flag.String("provider", "", "Modelgarden provider to test against")
	projectID = flag.String("projectid", "", "Modelgarden project")
	location  = flag.String("location", "us-east5", "Geographic location")
)

func TestAnthropicLive(t *testing.T) {
	if *provider != "anthropic" {
		t.Skipf("skipping Anthropic")
	}

	ctx := context.Background()
	g := genkit.Init(ctx, genkit.WithPlugins(&modelgarden.Anthropic{}))

	t.Run("invalid model", func(t *testing.T) {
		m := modelgarden.AnthropicModel(g, "claude-not-valid-v2")
		if m != nil {
			t.Fatalf("model should have been empty, got: %#v", m)
		}
	})

	t.Run("model version ok", func(t *testing.T) {
		m := modelgarden.AnthropicModel(g, "claude-opus-4")
		resp, err := genkit.Generate(ctx, g,
			ai.WithConfig(&ai.GenerationCommonConfig{
				Temperature: 1,
				Version:     "claude-opus-4@20250514",
			}),
			ai.WithModel(m),
			ai.WithSystem("talk to me like an evil pirate and say ARR several times but be very short"),
			ai.WithMessages(ai.NewUserMessage(ai.NewTextPart("I'm a fish"))),
		)
		if err != nil {
			t.Fatal(err)
		}

		if !strings.Contains(resp.Text(), "ARR") {
			t.Fatalf("not a pirate :( :%s", resp.Text())
		}
	})

	t.Run("model version nok", func(t *testing.T) {
		m := modelgarden.AnthropicModel(g, "claude-opus-4")
		_, err := genkit.Generate(ctx, g,
			ai.WithConfig(&ai.GenerationCommonConfig{
				Temperature: 1,
				Version:     "foo",
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
		m := modelgarden.AnthropicModel(g, "claude-opus-4")
		resp, err := genkit.Generate(ctx, g,
			ai.WithSystem("You are a professional image detective that talks like an evil pirate that loves animals, your task is to tell the name of the animal in the image but be very short"),
			ai.WithModel(m),
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

	t.Run("tools", func(t *testing.T) {
		m := modelgarden.AnthropicModel(g, "claude-opus-4")
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
			ai.WithPrompt("tell me a joke"),
			ai.WithTools(myJokeTool))
		if err != nil {
			t.Fatal(err)
		}

		if len(resp.Text()) == 0 {
			t.Fatal("expected a response but nothing was returned")
		}
	})

	t.Run("streaming", func(t *testing.T) {
		m := modelgarden.AnthropicModel(g, "claude-opus-4")
		out := ""
		parts := 0

		final, err := genkit.Generate(ctx, g,
			ai.WithPrompt("Tell me a short story about a frog and a princess"),
			ai.WithModel(m),
			ai.WithStreaming(func(ctx context.Context, c *ai.ModelResponseChunk) error {
				parts++
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

	t.Run("tools streaming", func(t *testing.T) {
		m := modelgarden.AnthropicModel(g, "claude-opus-4")
		out := ""
		parts := 0

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
			ai.WithTools(myStoryTool),
			ai.WithStreaming(func(ctx context.Context, c *ai.ModelResponseChunk) error {
				parts++
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
}

func fetchImgAsBase64() (string, error) {
	// CC0 license image
	imgUrl := "https://pd.w.org/2025/07/896686fbbcd9990c9.84605288-2048x1365.jpg"
	resp, err := http.Get(imgUrl)
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
