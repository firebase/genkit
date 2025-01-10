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

package genkit

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/base"
)

var chatGenkit, _ = New(nil)
var chatModel = getChatModel(chatGenkit)
var chatTool = getNameTool(chatGenkit)

func getNameTool(g *Genkit) *ai.ToolDef[struct{ Name string }, string] {
	return DefineTool(g, "updateName", "use this tool to update the name of the user",
		func(ctx context.Context, input struct {
			Name string
		}) (string, error) {
			// TODO: set name in state when Genkit registry is per instance
			// SessionFromContext(ctx, g).UpdateState(input.Name)
			return input.Name, nil
		},
	)
}

func getChatModel(g *Genkit) ai.Model {
	return ai.DefineModel(g.reg, "test", "chat", nil, func(ctx context.Context, gr *ai.ModelRequest, msc ai.ModelStreamingCallback) (*ai.ModelResponse, error) {
		if msc != nil {
			msc(ctx, &ai.ModelResponseChunk{
				Content: []*ai.Part{ai.NewTextPart("3!")},
			})
			msc(ctx, &ai.ModelResponseChunk{
				Content: []*ai.Part{ai.NewTextPart("2!")},
			})
			msc(ctx, &ai.ModelResponseChunk{
				Content: []*ai.Part{ai.NewTextPart("1!")},
			})
		}

		textResponse := ""
		var contentTexts []string
		for _, m := range gr.Messages {
			if m.Role != ai.RoleUser && m.Role != ai.RoleModel {
				textResponse += fmt.Sprintf("%s: ", m.Role)
			}

			for _, c := range m.Content {
				contentTexts = append(contentTexts, c.Text)
			}
		}

		textResponse += strings.Join(contentTexts, "; ")
		textResponse += "; config: " + base.PrettyJSONString(gr.Config)
		textResponse += "; context: " + base.PrettyJSONString(gr.Context)

		return &ai.ModelResponse{
			Request: gr,
			Message: ai.NewModelTextMessage(fmt.Sprintf("Echo: %s", textResponse)),
		}, nil
	})
}

func TestChat(t *testing.T) {
	ctx := context.Background()

	chat, err := NewChat(ctx, chatGenkit, WithModel(chatModel))
	if err != nil {
		t.Fatal(err.Error())
	}

	resp, err := chat.Send(ctx, "Tell me a joke")
	if err != nil {
		t.Fatal(err.Error())
	}

	want := "Echo: Tell me a joke; config: null; context: null"
	if resp.Text() != want {
		t.Errorf("got %q want %q", resp.Text(), want)
	}

	resp, err = chat.Send(ctx, "Bye")
	if err != nil {
		t.Fatal(err.Error())
	}

	want = "Echo: Tell me a joke; Echo: Tell me a joke; config: null; context: null; Bye; config: null; context: null"
	if resp.Text() != want {
		t.Errorf("got %q want %q", resp.Text(), want)
	}

	// Should this be 4?
	if len(resp.Request.Messages) != 3 {
		t.Errorf("no history, got %d message want %d", len(resp.Request.Messages), 3)
	}
}

func TestChatWithStreaming(t *testing.T) {
	ctx := context.Background()

	streamText := ""
	chat, err := NewChat(
		ctx,
		chatGenkit,
		WithModel(chatModel),
		WithStreaming(func(ctx context.Context, grc *ai.ModelResponseChunk) error {
			streamText += grc.Text()
			return nil
		}),
	)
	if err != nil {
		t.Fatal(err.Error())
	}

	resp, err := chat.Send(ctx, "Hello")
	if err != nil {
		t.Fatal(err.Error())
	}

	want := "Echo: Hello; config: null; context: null"
	if resp.Text() != want {
		t.Errorf("got %q want %q", resp.Text(), want)
	}

	want = "3!2!1!"
	if streamText != want {
		t.Errorf("got %q want %q", streamText, want)
	}
}

func TestChatWithOptions(t *testing.T) {
	ctx := context.Background()

	session, err := NewSession(chatGenkit)
	if err != nil {
		t.Fatal(err.Error())
	}

	chat, err := NewChat(
		ctx,
		chatGenkit,
		WithModel(chatModel),
		WithSession(session),
		WithThreadName("test"),
		WithSystemText("you are a helpful assistant"),
		WithConfig(ai.GenerationCommonConfig{Temperature: 1}),
		WithContext("foo", "bar"),
		WithTools(chatTool),
		WithOutputSchema("hello world"),
		WithOutputFormat(ai.OutputFormatText),
	)
	if err != nil {
		t.Fatal(err.Error())
	}

	if chat.Session == nil || chat.Session.ID != session.ID {
		t.Errorf("session is not set")
	}

	if chat.ThreadName != "test" {
		t.Errorf("thread name is not set")
	}

	if !strings.Contains(chat.SystemText, "you are a helpful assistant") {
		t.Errorf("system text is not set")
	}

	if chat.Request.Schema == nil {
		t.Errorf("output schema not set")
	}

	if chat.Request.Format != ai.OutputFormatText {
		t.Errorf("output format is not set")
	}

	resp, err := chat.Send(ctx, "Hello")
	if err != nil {
		t.Fatal(err.Error())
	}

	want := "Echo: system: you are a helpful assistant; Hello; config: {\n  \"temperature\": 1\n}; context: [\n  \"foo\",\n  \"bar\"\n]"
	if resp.Text() != want {
		t.Errorf("got %q want %q", resp.Text(), want)
	}
}

func TestChatWithOptionsErrorHandling(t *testing.T) {
	session, err := NewSession(chatGenkit)
	if err != nil {
		t.Fatal(err.Error())
	}

	var tests = []struct {
		name string
		with ChatOption
	}{
		{
			name: "WithSession",
			with: WithSession(session),
		},
		{
			name: "WithThreadName",
			with: WithThreadName("test"),
		},
		{
			name: "WithStreaming",
			with: WithStreaming(func(ctx context.Context, grc *ai.ModelResponseChunk) error {
				return nil
			}),
		},
		{
			name: "WithSystemText",
			with: WithSystemText("system text"),
		},
		{
			name: "WithConfig",
			with: WithConfig(ai.GenerationCommonConfig{}),
		},
		{
			name: "WithContext",
			with: WithContext("foo", "bar"),
		},
		{
			name: "WithTools",
			with: WithTools(chatTool),
		},
		{
			name: "WithOutputSchema",
			with: WithOutputSchema(map[string]any{"name": "world"}),
		},
		{
			name: "WithOutputFormat",
			with: WithOutputFormat(ai.OutputFormatJSON),
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			_, err := NewChat(
				context.Background(),
				chatGenkit,
				WithModel(chatModel),
				test.with,
				test.with,
			)

			if err == nil {
				t.Errorf("%s could be set twice", test.name)
			}
		})
	}
}

func TestMultiChatSession(t *testing.T) {
	ctx := context.Background()

	session, err := NewSession(chatGenkit)
	if err != nil {
		t.Fatal(err.Error())
	}

	lawyerChat, err := NewChat(
		ctx,
		chatGenkit,
		WithModel(chatModel),
		WithThreadName("lawyer thread"),
		WithSystemText("talk like a lawyer"),
		WithSession(session),
	)
	if err != nil {
		t.Fatal(err.Error())
	}

	resp, err := lawyerChat.Send(ctx, "Hello lawyer")
	if err != nil {
		t.Fatal(err.Error())
	}

	want := "Echo: system: talk like a lawyer; Hello lawyer; config: null; context: null"
	if resp.Text() != want {
		t.Errorf("got %q want %q", resp.Text(), want)
	}

	pirateChat, err := NewChat(
		ctx,
		chatGenkit,
		WithModel(chatModel),
		WithThreadName("pirate thread"),
		WithSystemText("talk like a pirate"),
		WithSession(session),
	)
	if err != nil {
		t.Fatal(err.Error())
	}

	resp, err = pirateChat.Send(ctx, "Hello pirate")
	if err != nil {
		t.Fatal(err.Error())
	}

	want = "Echo: system: talk like a pirate; Hello pirate; config: null; context: null"
	if resp.Text() != want {
		t.Errorf("got %q want %q", resp.Text(), want)
	}

	if len(session.SessionData.Threads) != 2 {
		t.Errorf("session should have 2 threads")
	}
}
