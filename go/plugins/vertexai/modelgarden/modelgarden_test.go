// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelgarden_test

import (
	"context"
	"encoding/base64"
	"flag"
	"fmt"
	"io"
	"net/http"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/vertexai/modelgarden"
)

var (
	projectID = flag.String("projectid", "", "Modelgarden project")
	location  = flag.String("location", "us-east5", "Geographic location")
)

// go test . -v -projectid="my_projectId"
func TestModelGarden(t *testing.T) {
	if *projectID == "" {
		t.Skipf("no -projectid provided")
	}

	ctx := context.Background()
	g, err := genkit.New(nil)
	if err != nil {
		t.Fatal(err)
	}

	err = modelgarden.Init(ctx, g, &modelgarden.Config{
		ProjectID: *projectID,
		Location:  *location,
		Models:    []string{"claude-3-5-sonnet-v2"},
	})
	if err != nil {
		t.Fatal(err)
	}

	t.Run("invalid model", func(t *testing.T) {
		t.Skipf("no streaming support yet")
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-not-valid-v2")
		if m != nil {
			t.Fatal("model should have been invalid")
		}
	})

	t.Run("model version ok", func(t *testing.T) {
		t.Skipf("no streaming support yet")
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-3-5-sonnet-v2")
		resp, err := genkit.Generate(ctx, g,
			ai.WithConfig(&ai.GenerationCommonConfig{
				Temperature: 1,
				Version:     "claude-3-5-sonnet-v2@20241022",
			}),
			ai.WithModel(m),
			ai.WithSystemPrompt("talk to me like an evil pirate and say ARR several times but be very short"),
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
		t.Skipf("no streaming support yet")
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-3-5-sonnet-v2")
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
		t.Skipf("no streaming support yet")
		i, err := fetchImgAsBase64()
		if err != nil {
			t.Fatal(err)
		}
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-3-5-sonnet-v2")
		resp, err := genkit.Generate(ctx, g,
			ai.WithSystemPrompt("You are a professional image detective that talks like an evil pirate that does not like tv shows, your task is to tell the name of the character in the image but be very short"),
			ai.WithModel(m),
			ai.WithMessages(
				ai.NewUserMessage(
					ai.NewTextPart("do you know who's in the image?"),
					ai.NewMediaPart("", "data:image/png;base64,"+i))))
		if err != nil {
			t.Fatal(err)
		}

		if !strings.Contains(resp.Text(), "Bluey") {
			t.Fatalf("it should've said Bluey but got: %s", resp.Text())
		}
	})

	t.Run("tools", func(t *testing.T) {
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-3-5-sonnet-v2")
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
			ai.WithTextPrompt("tell me a joke"),
			ai.WithTools(myJokeTool))
		if err != nil {
			t.Fatal(err)
		}

		fmt.Printf("resp: %s\n\n", resp.Text())
	})

	t.Run("streaming", func(t *testing.T) {
		t.Skipf("no streaming support yet")
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-3-5-sonnet-v2")
		out := ""
		parts := 0

		final, err := genkit.Generate(ctx, g,
			ai.WithTextPrompt("Tell me a short story about a frog and a princess"),
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
			t.Fatalf("streaming and final should containt the same text.\nstreaming: %s\nfinal:%s\n", out, out2)
		}
		if final.Usage.InputTokens == 0 || final.Usage.OutputTokens == 0 || final.Usage.TotalTokens == 0 {
			t.Fatalf("empty usage stats: %#v", *final.Usage)
		}
	})
}

// Bluey rocks
func fetchImgAsBase64() (string, error) {
	imgUrl := "https://www.bluey.tv/wp-content/uploads/2023/07/Bluey.png"
	resp, err := http.Get(imgUrl)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", err
	}

	// keep the img in memory
	imageBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	base64string := base64.StdEncoding.EncodeToString(imageBytes)
	return base64string, nil
}
