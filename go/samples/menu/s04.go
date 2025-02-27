// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/dotprompt"
	"github.com/firebase/genkit/go/plugins/localvec"
)

func setup04(g *genkit.Genkit, indexer ai.Indexer, retriever ai.Retriever, model ai.Model) error {
	ragDataMenuPrompt, err := dotprompt.Define(g, "s04_ragDataMenu",
		`
		  You are acting as Walt, a helpful AI assistant here at the restaurant.
		  You can answer questions about the food on the menu or any other questions
		  customers have about food in general.

		  Here are some items that are on today's menu that are relevant to
		  helping you answer the customer's question:
		  {{#each menuData~}}
		  - {{this.title}} \${{this.price}}
		    {{this.description}}
		  {{~/each}}

		  Answer this customer's question:
		  {{question}}?`,
		dotprompt.WithDefaultModel(model),
		dotprompt.WithInputType(dataMenuQuestionInput{}),
		dotprompt.WithOutputFormat(ai.OutputFormatText),
		dotprompt.WithDefaultConfig(&ai.GenerationCommonConfig{
			Temperature: 0.3,
		}),
	)
	if err != nil {
		return err
	}

	type flowOutput struct {
		Rows int `json:"rows"`
	}

	genkit.DefineFlow(g, "s04_indexMenuItems",
		func(ctx context.Context, input []*menuItem) (*flowOutput, error) {
			var docs []*ai.Document
			for _, m := range input {
				s := fmt.Sprintf("%s %g \n %s", m.Title, m.Price, m.Description)
				metadata := map[string]any{
					"menuItem": m,
				}
				docs = append(docs, ai.DocumentFromText(s, metadata))
			}
			if err := ai.Index(ctx, indexer, ai.WithIndexerDocs(docs...)); err != nil {
				return nil, err
			}

			ret := &flowOutput{
				Rows: len(input),
			}
			return ret, nil
		},
	)

	genkit.DefineFlow(g, "s04_ragMenuQuestion",
		func(ctx context.Context, input *menuQuestionInput) (*answerOutput, error) {
			resp, err := ai.Retrieve(ctx, retriever,
				ai.WithRetrieverText(input.Question),
				ai.WithRetrieverOpts(&localvec.RetrieverOptions{
					K: 3,
				}))
			if err != nil {
				return nil, err
			}

			var menuItems []*menuItem
			for _, doc := range resp.Documents {
				menuItems = append(menuItems, doc.Metadata["menuItem"].(*menuItem))
			}
			questionInput := &dataMenuQuestionInput{
				MenuData: menuItems,
				Question: input.Question,
			}

			presp, err := ragDataMenuPrompt.Generate(ctx, g, dotprompt.WithInput(questionInput))
			if err != nil {
				return nil, err
			}

			ret := &answerOutput{
				Answer: presp.Message.Content[0].Text,
			}
			return ret, nil
		},
	)

	return nil
}
