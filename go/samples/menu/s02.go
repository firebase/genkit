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
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/dotprompt"
)

var s02DataMenuPrompt *dotprompt.Prompt

func init() {
	var err error
	s02DataMenuPrompt, err = dotprompt.Define("s02_dataMenu",
		`You are acting as a helpful AI assistant named Walt that can answer 
		 questions about the food available on the menu at Walt's Burgers. 

		 Answer this customer's question, in a concise and helpful manner,
		 as long as it is about food on the menu or something harmless like sports.
		 Use the tools available to answer menu questions.
		 DO NOT INVENT ITEMS NOT ON THE MENU.

		 Question:
		 {{question}} ?`,
		&dotprompt.Config{
			Model: "google-vertexai/gemini-1.0-pro",
			InputSchema: menuQuestionInputSchema,
			OutputFormat: ai.OutputFormatText,
			Tools: []*ai.ToolDefinition{
				menuToolDef,
			},
		},
	)
	if err != nil {
		log.Fatal(err)
	}
}

var menuToolDef = &ai.ToolDefinition{
	Name:        "todaysMenu",
	OutputSchema: map[string]any{
		"menuData": []menuItem{},
	},
}

func menu(ctx context.Context, input map[string]any) (map[string]any, error) {
	fmt.Println("********** called menu **********")

	f, err := os.Open("testdata/menu.json")
	if err != nil {
		return nil, err
	}
	decoder := json.NewDecoder(f)
	var m map[string]any
	if err := decoder.Decode(&m); err != nil {
		return nil, err
	}
	return m, nil
}

func init() {
	ai.RegisterTool("menu", menuToolDef, nil, menu)
}

var s02MenuQuestionFlow = genkit.DefineFlow("s02_menuQuestion",
	func(ctx context.Context, input *menuQuestionInput, _ genkit.NoStream) (*answerOutput, error) {
		vars, err := s02DataMenuPrompt.BuildVariables(input)
		if err != nil {
			return nil, err
		}
		ai := &dotprompt.ActionInput{Variables: vars}

		resp, err := s02DataMenuPrompt.Execute(ctx, ai)
		if err != nil {
			return nil, err
		}

		text, err := resp.Text()
		if err != nil {
			return nil, fmt.Errorf("s02MenuQuestionFlow: %v", err)
		}
		return &answerOutput{Answer: text}, nil
	},
)
