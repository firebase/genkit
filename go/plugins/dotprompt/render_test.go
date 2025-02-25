// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package dotprompt

import (
	"context"
	"fmt"
	"log"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/google/go-cmp/cmp"
)

// TestRender is some of the tests from prompt_test.ts.
func TestRender(t *testing.T) {
	g, err := genkit.Init(context.Background(), genkit.WithPromptDir("testdata"))
	if err != nil {
		log.Fatal(err)
	}

	var tests = []struct {
		prompt string
		input  map[string]any
		want   string
		bad    bool
	}{
		{
			prompt: "Hello {{name}}, how are you?",
			input: map[string]any{
				"name": "Michael",
			},
			want: "Hello Michael, how are you?",
		},
		{
			prompt: `---
input:
  default:
    name: "Fellow Human"
---
Hello {{name}}, how are you?`,
			input: nil,
			want:  "Hello Fellow Human, how are you?",
		},
		{
			prompt: `---
input: {
  isInvalid: true
  wasInvalid: true
}
---

This is the rest of the prompt`,
			bad: true,
		},
	}

	for i, test := range tests {
		t.Run(fmt.Sprintf("%d", i), func(t *testing.T) {
			prompt, err := Parse(g, t.Name(), "", []byte(test.prompt))
			if err != nil {
				if test.bad {
					t.Logf("got expected error %v", err)
					return
				}
				t.Fatal(err)
			}
			if test.bad {
				t.Fatal("test succeeded unexpectedly")
			}
			got, err := prompt.RenderText(test.input)
			if err != nil {
				t.Fatal(err)
			}
			if got != test.want {
				t.Errorf("got %q, want %q", got, test.want)
			}
		})
	}
}

// TestRenderMessages is some of the tests from template_test.ts.
func TestRenderMessages(t *testing.T) {
	g, err := genkit.Init(context.Background(), genkit.WithPromptDir("testdata"))
	if err != nil {
		log.Fatal(err)
	}

	var tests = []struct {
		name     string
		template string
		input    map[string]any
		want     []*ai.Message
	}{
		{
			name:     "inject variables",
			template: "Hello {{name}}",
			input:    map[string]any{"name": "World"},
			want: []*ai.Message{
				{
					Role: ai.RoleUser,
					Content: []*ai.Part{
						ai.NewTextPart("Hello World"),
					},
				},
			},
		},
		{
			name:     "allow multipart with url",
			template: `{{media url=image}} Describe the image above.`,
			input: map[string]any{
				"image": "https://some.image.url/image.jpg",
			},
			want: []*ai.Message{
				{
					Role: ai.RoleUser,
					Content: []*ai.Part{
						ai.NewMediaPart("", "https://some.image.url/image.jpg"),
						ai.NewTextPart(" Describe the image above."),
					},
				},
			},
		},
		{
			name:     "allow multiple media parts, adjacent or separated by text",
			template: `Look at these images: {{#each images}}{{media url=.}} {{/each}} Do you like them? Here is another: {{media url=anotherImage}}`,
			input: map[string]any{
				"images": []string{
					"http://1.png",
					"https://2.png",
					"data:image/jpeg;base64,abc123",
				},
				"anotherImage": "http://anotherImage.png",
			},
			want: []*ai.Message{
				{
					Role: ai.RoleUser,
					Content: []*ai.Part{
						ai.NewTextPart("Look at these images: "),
						ai.NewMediaPart("", "http://1.png"),
						ai.NewMediaPart("", "https://2.png"),
						ai.NewMediaPart("", "data:image/jpeg;base64,abc123"),
						ai.NewTextPart("  Do you like them? Here is another: "),
						ai.NewMediaPart("", "http://anotherImage.png"),
					},
				},
			},
		},
		{
			name: "allow changing the role at the beginning",
			template: `  {{role "system"}}You are super helpful.
      {{~role "user"}}Do something!`,
			want: []*ai.Message{
				{
					Role: ai.RoleSystem,
					Content: []*ai.Part{
						ai.NewTextPart("You are super helpful."),
					},
				},
				{
					Role: ai.RoleUser,
					Content: []*ai.Part{
						ai.NewTextPart("Do something!"),
					},
				},
			},
		},
		{
			name: "allow rendering JSON",
			input: map[string]any{
				"test": true,
			},
			template: "{{json .}}",
			want: []*ai.Message{
				{
					Role: ai.RoleUser,
					Content: []*ai.Part{
						ai.NewTextPart(`{"test":true}`),
					},
				},
			},
		},
		{
			name: "allow indenting JSON",
			input: map[string]any{
				"test": true,
			},
			template: "{{json . indent=2}}",
			want: []*ai.Message{
				{
					Role: ai.RoleUser,
					Content: []*ai.Part{
						ai.NewTextPart("{\n  \"test\": true\n}"),
					},
				},
			},
		},
	}

	cmpPart := func(a, b *ai.Part) bool {
		if a.IsText() != b.IsText() {
			return false
		}
		if a.Text != b.Text {
			return false
		}
		if a.ContentType != b.ContentType {
			return false
		}
		return true
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			prompt, err := Parse(g, t.Name(), "", []byte(test.template))
			if err != nil {
				t.Fatal(err)
			}
			got, err := prompt.RenderMessages(test.input)
			if err != nil {
				t.Fatal(err)
			}
			if diff := cmp.Diff(test.want, got, cmp.Comparer(cmpPart)); diff != "" {
				t.Errorf("mismatch (-want, +got):\n%s", diff)
			}
		})
	}
}
