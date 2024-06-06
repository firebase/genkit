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

package main

import (
	"context"
	"slices"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/dotprompt"
)

type chatSessionInput struct {
	SessionID string `json:"sessionID"`
	Question  string `json:"question"`
}

type chatSessionOutput struct {
	SessionID string        `json:"sessionID"`
	History   []*ai.Message `json:"history"`
}

// Very simple local storage for chat history.
// Each conversation is identified by a sessionID generated by the application.
// The history has a preamble of message, which serves as a system prompt.

type chatHistory []*ai.Message

type chatHistoryStore struct {
	preamble chatHistory
	sessions map[string]chatHistory
}

func (ch *chatHistoryStore) Store(sessionID string, history chatHistory) {
	ch.sessions[sessionID] = history
}

func (ch *chatHistoryStore) Retrieve(sessionID string) chatHistory {
	if h, ok := ch.sessions[sessionID]; ok {
		return h
	}
	return ch.preamble
}

func setup03(ctx context.Context, generator *ai.GeneratorAction) error {
	chatPreamblePrompt, err := dotprompt.Define("s03_chatPreamble",
		`
		  {{ role "user" }}
		  Hi. What's on the menu today?

		  {{ role "model" }}
		  I am Walt, a helpful AI assistant here at the restaurant.
		  I can answer questions about the food on the menu or any other questions
		  you have about food in general. I probably can't help you with anything else.
		  Here is today's menu:
		  {{#each menuData~}}
		  - {{this.title}} \${{this.price}}
		    {{this.description}}
		  {{~/each}}
		  Do you have any questions about the menu?`,
		dotprompt.Config{
			Generator:    generator,
			InputSchema:  dataMenuQuestionInputSchema,
			OutputFormat: ai.OutputFormatText,
			GenerationConfig: &ai.GenerationCommonConfig{
				Temperature: 0.3,
			},
		},
	)
	if err != nil {
		return err
	}

	menuData, err := menu(context.Background(), nil)
	if err != nil {
		return err
	}

	preamble, err := chatPreamblePrompt.RenderMessages(map[string]any{
		"menuData": menuData,
		"question": "",
	})
	if err != nil {
		return err
	}

	storedHistory := &chatHistoryStore{
		preamble: chatHistory(preamble),
		sessions: make(map[string]chatHistory),
	}

	genkit.DefineFlow("s03_multiTurnChat",
		func(ctx context.Context, input *chatSessionInput, _ genkit.NoStream) (*chatSessionOutput, error) {
			history := storedHistory.Retrieve(input.SessionID)
			msg := &ai.Message{
				Content: []*ai.Part{
					ai.NewTextPart(input.Question),
				},
				Role: ai.RoleUser,
			}
			messages := append(slices.Clip(history), msg)
			req := &ai.GenerateRequest{
				Messages: messages,
			}
			resp, err := ai.Generate(ctx, generator, req, nil)
			if err != nil {
				return nil, err
			}

			messages = append(messages, resp.Candidates[0].Message)
			storedHistory.Store(input.SessionID, messages)

			out := &chatSessionOutput{
				SessionID: input.SessionID,
				History:   messages,
			}
			return out, nil
		},
	)

	return nil
}
