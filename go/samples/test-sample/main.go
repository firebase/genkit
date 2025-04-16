package main

import (
	"context"
	"fmt"
	"log"
	"net/http"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/server"
)

// Input struct for the weather prompt and tool.
type WeatherQuery struct {
	Location string `json:"location"`
}

// Output struct for the weather prompt.
type Weather struct {
	Report string `json:"report"`
}

// Task struct for the task list.
type Task struct {
	Title        string `json:"title"`
	TimeEstimate string `json:"timeEstimate"`
}

func main() {
	ctx := context.Background()

	g, err := genkit.Init(ctx,
		genkit.WithDefaultModel("googleai/gemini-2.0-flash"),
		genkit.WithPlugins(&googlegenai.GoogleAI{}),
	)
	if err != nil {
		log.Fatal(err)
	}

	// Define a tool that simulates fetching weather.
	weatherTool := genkit.DefineTool(g, "weatherTool",
		"Use this tool to get the weather report for a specific location",
		func(ctx *ai.ToolContext, input WeatherQuery) (string, error) {
			report := fmt.Sprintf("The weather in %s is sunny and 70 degrees today.", input.Location)
			return report, nil
		},
	)

	// Define a prompt that uses the weather tool.
	weatherPrompt, err := genkit.DefinePrompt(
		g, "weatherPrompt",
		ai.WithSystem("You are a helpful weather assistant. When using tools, respond with the output of the tool call."),
		ai.WithPrompt("What's the weather like in {{location}}?"),
		ai.WithTools(weatherTool),
		ai.WithInputType(WeatherQuery{Location: "San Francisco"}), // Defaults to San Francisco.
		ai.WithOutputType(Weather{}),
	)
	if err != nil {
		log.Fatal(err)
	}

	// Define a flow that takes a location and returns the weather report.
	weatherFlow := genkit.DefineFlow(g, "weatherFlow", func(ctx context.Context, location string) (*Weather, error) {
		resp, err := weatherPrompt.Execute(ctx,
			ai.WithConfig(&googlegenai.GeminiConfig{Temperature: 0.7}),
			ai.WithInput(WeatherQuery{Location: location}),
		)
		if err != nil {
			return nil, fmt.Errorf("error executing weather prompt: %w", err)
		}

		var out Weather
		if err = resp.Output(&out); err != nil {
			return nil, fmt.Errorf("error parsing weather output: %w", err)
		}

		return &out, nil
	})

	// Define a flow that greets the user in the morning with the details about their day.
	genkit.DefineFlow(g, "morningGreetingFlow", func(ctx context.Context, taskCount int) (string, error) {
		if taskCount == 0 {
			taskCount = 3
		}

		weather, err := weatherFlow.Run(ctx, "San Francisco")
		if err != nil {
			return "", fmt.Errorf("error executing weather flow: %w", err)
		}

		taskList, _, err := genkit.GenerateData[[]Task](ctx, g,
			ai.WithPrompt("Generate a list of %d every-day tasks for me to do today.", taskCount),
		)
		if err != nil {
			return "", fmt.Errorf("error generating task list: %w", err)
		}

		taskListStr := ""
		for _, task := range *taskList {
			taskListStr += fmt.Sprintf(" - %s (%s)\n", task.Title, task.TimeEstimate)
		}

		actionCtx := core.FromContext(ctx)
		user := "guest"
		if actionCtx["user"] != nil {
			user = actionCtx["user"].(string)
		}

		return fmt.Sprintf("Good morning, %s! %s\n\nHere are some tasks for you to complete today:\n%s", user, weather.Report, taskListStr), nil
	})

	// Serve the defined flows.
	mux := http.NewServeMux()
	for _, a := range genkit.ListFlows(g) {
		mux.HandleFunc("POST /"+a.Name(), genkit.Handler(a, genkit.WithContextProviders(contextProvider)))
	}
	log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
}

/*

Call your flow with the following command:

curl -X POST http://localhost:8080/morningGreetingFlow \
  -H "Content-Type: application/json" \
  -H "Authorization: secret-token" \
  -d '{"data": 3}'

*/

// contextProvider simulates auth.
func contextProvider(ctx context.Context, req core.RequestData) (core.ActionContext, error) {
	user := "guest"
	if req.Headers["authorization"] == "secret-token" {
		user = "Alex"
	}

	return core.ActionContext{"user": user}, nil
}
