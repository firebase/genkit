package main

import (
	"context"
	"errors"
	"fmt"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/vertexai"
	"log"
	"time"
)

func main() {
	ctx := context.Background()
	if err := vertexai.Init(ctx, nil); err != nil {
		log.Fatal(err)
	}
	m := vertexai.Model("gemini-1.5-flash")
	if m == nil {
		log.Fatal(errors.New("vertexai init failed"))
	}
	resp, err := ai.Generate(ctx, m,
		ai.WithConfig(&ai.GenerationCommonConfig{Temperature: 1, TTL: time.Hour}),
		ai.WithTextPrompt("Tell me a joke about golang developers"))

	if err != nil {
		fmt.Println(err)
	}
	fmt.Println("output:", resp.Message.Text())
}
