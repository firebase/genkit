package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"google.golang.org/genai"
)

func main() {
	ctx := context.Background()

	// Initialize Genkit with the Google AI plugin and Gemini 2.0 Flash.
	g, err := genkit.Init(ctx,
		genkit.WithPlugins(&googlegenai.GoogleAI{}),
	)
	if err != nil {
		log.Fatalf("could not initialize Genkit: %v", err)
	}

	resp, err := genkit.GenerateOperation(ctx, g,
		ai.WithMessages(ai.NewUserTextMessage("Mouse eating cheese")),
		ai.WithModelName("googleai/veo-2.0-generate-001"),
		ai.WithConfig(&genai.GenerateVideosConfig{
			NumberOfVideos:  1,
			AspectRatio:     "16:9",
			DurationSeconds: genai.Ptr(int32(5)),
		}))
	if resp != nil {
		opJson, _ := json.Marshal(resp.Output)
		fmt.Printf("%s", opJson)
	}
	if err != nil {
		log.Fatalf("could not generate model response: %v", err)
	}

	// log.Println(resp.Text())
}
