package main

import (
	"context"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx := context.Background()
	g := genkit.Init(ctx,
		genkit.WithPlugins(&googlegenai.GoogleAI{}),
		genkit.WithDefaultModel("googleai/gemini-2.5-flash"),
	)

	inputSchema := map[string]any{
		"type": "object",
		"properties": map[string]any{
			"id": map[string]any{
				"name":        "id",
				"description": "The id to be printed.",
				"type":        "integer",
			}},
		"required": []any{"id"},
	}

	executeFn := func(ctx *ai.ToolContext, input any) (string, error) {
		inputMap, ok := input.(map[string]any)
		if !ok {
			// If the input is not a map, return an error indicating the type mismatch.
			log.Fatalf("tool input expected map[string]any, got %T", input)
		}
		id := inputMap["id"]
		fmt.Printf("input received of type '%T'", id)

		strResult := fmt.Sprintf("%v", id)
		return strResult, nil
	}

	genkitTool := genkit.DefineToolWithInputSchema(
		g,
		"example_tool",
		"prints the id given to the tool",
		inputSchema,
		executeFn,
	)

	resp, err := genkitTool.RunRaw(ctx, map[string]any{
		"id": int64(1),
	})
	if err != nil {
		log.Fatal("error invoking the tool")
	}
	fmt.Println(resp)

}
