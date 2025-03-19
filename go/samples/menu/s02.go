// Copyright 2025 Google LLC
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

	dataMenuPrompt, err := genkit.DefinePrompt(g, "s02_dataMenu",
		ai.WithPromptText(`
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
	if err != nil {
		return err
	}

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
