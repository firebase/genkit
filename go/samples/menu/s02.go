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

package main

import (
	"context"
	"encoding/json"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

func menu(ctx *ai.ToolContext, _ any) ([]*menuItem, error) {
	f, err := os.Open("testdata/menu.json")
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var s []*menuItem
	if err := json.NewDecoder(f).Decode(&s); err != nil {
		return nil, err
	}
	return s, nil
}

func setup02(g *genkit.Genkit, m ai.Model) error {
	menuTool := genkit.DefineTool(g, "todaysMenu", "Use this tool to retrieve all the items on today's menu", menu)

	dataMenuPrompt := genkit.DefinePrompt(g, "s02_dataMenu",
		ai.WithPrompt(`
You are acting as a helpful AI assistant named Walt that can answer
questions about the food available on the menu at Walt's Burgers.

Answer this customer's question, in a concise and helpful manner,
as long as it is about food on the menu or something harmless like sports.
Use the tools available to answer menu questions.
DO NOT INVENT ITEMS NOT ON THE MENU.

Question:
{{question}} ?`),
		ai.WithModel(m),
		ai.WithInputType(menuQuestionInput{}),
		ai.WithTools(menuTool),
	)

	genkit.DefineFlow(g, "s02_menuQuestion",
		func(ctx context.Context, input *menuQuestionInput) (*answerOutput, error) {
			resp, err := dataMenuPrompt.Execute(ctx, ai.WithInput(input))
			if err != nil {
				return nil, err
			}

			return &answerOutput{Answer: resp.Text()}, nil
		},
	)

	return nil
}
