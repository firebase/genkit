package main

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/evaluators"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx := context.Background()

	g := genkit.Init(ctx,
		genkit.WithPlugins(
			&googlegenai.GoogleAI{},
			&evaluators.GenkitEval{
				Metrics: []evaluators.MetricConfig{
					{
						MetricType: evaluators.EvaluatorRegex,
					},
				},
			},
		),
		genkit.WithDefaultModel("googleai/gemini-2.5-flash"),
		genkit.WithPromptDir("prompts"),
	)

	codePrompt := genkit.DefinePrompt(g, "codePrompt",
		ai.WithModelName("googleai/gemini-2.5-flash"),
		ai.WithPrompt("Define the word '{{subject}}' in one sentence."),
		ai.WithInputType(map[string]any{"subject": ""}),
	)

	definePromptFlow(g, "simple", "simple", ctx)
	definePromptFlow(g, "no_model", "no_model", ctx)
	definePromptFlow(g, "with_config", "with_config", ctx)
	definePromptFlowFromPrompt(g, "codePromptFlow", codePrompt, ctx)

	<-ctx.Done()
}

// Helper to define a flow that executes a loaded prompt by its name.
func definePromptFlow(g *genkit.Genkit, flowName, promptName string, ctx context.Context) {
	genkit.DefineFlow(g, flowName, func(ctx context.Context, input map[string]string) (string, error) {
		p := genkit.LookupPrompt(g, promptName)
		if p == nil {
			return "", fmt.Errorf("prompt %q not found", promptName)
		}
		resp, err := p.Execute(ctx, ai.WithInput(input))
		if err != nil {
			return "", err
		}
		return resp.Text(), nil
	})
}

// Helper to define a flow that executes a directly provided prompt.
func definePromptFlowFromPrompt(g *genkit.Genkit, flowName string, p ai.Prompt, ctx context.Context) {
	genkit.DefineFlow(g, flowName, func(ctx context.Context, input map[string]string) (string, error) {
		resp, err := p.Execute(ctx, ai.WithInput(input))
		if err != nil {
			return "", err
		}
		return resp.Text(), nil
	})
}
