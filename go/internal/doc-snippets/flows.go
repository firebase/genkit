// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package snippets

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"strings"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/genkit"
)

func f1() {
	ctx := context.Background()
	g, _ := genkit.Init(ctx)

	// [START flow1]
	menuSuggestionFlow := genkit.DefineFlow(
		g,
		"menuSuggestionFlow",
		func(ctx context.Context, restaurantTheme string) (string, error) {
			suggestion := makeMenuItemSuggestion(restaurantTheme)
			return suggestion, nil
		})
	// [END flow1]
	_ = menuSuggestionFlow

}

// [START msug]
type MenuSuggestion struct {
	ItemName    string `json:"item_name"`
	Description string `json:"description"`
	Calories    int    `json:"calories"`
}

// [END msug]

func makeMenuItemSuggestion(string) string { return "" }

func f2() {
	ctx := context.Background()
	g, _ := genkit.Init(ctx)

	// [START flow2]
	menuSuggestionFlow := genkit.DefineFlow(
		g,
		"menuSuggestionFlow",
		func(ctx context.Context, restaurantTheme string) (MenuSuggestion, error) {
			suggestion := makeStructuredMenuItemSuggestion(restaurantTheme)
			return suggestion, nil
		},
	)
	// [END flow2]
	// [START run1]
	suggestion, err := menuSuggestionFlow.Run(context.Background(), "French")
	// [END run1]
	_ = suggestion
	_ = err
}

// [START streaming-types]
// Types for illustrative purposes.
type InputType string
type OutputType string
type StreamType string

// [END streaming-types]

func f3() {
	ctx := context.Background()
	g, _ := genkit.Init(ctx)

	// [START streaming]
	menuSuggestionFlow := genkit.DefineStreamingFlow(
		g,
		"menuSuggestionFlow",
		func(
			ctx context.Context,
			restaurantTheme InputType,
			callback func(context.Context, StreamType) error,
		) (OutputType, error) {
			var menu strings.Builder
			menuChunks := make(chan StreamType)
			go makeFullMenuSuggestion(restaurantTheme, menuChunks)
			for {
				chunk, ok := <-menuChunks
				if !ok {
					break
				}
				if callback != nil {
					callback(context.Background(), chunk)
				}
				menu.WriteString(string(chunk))
			}
			return OutputType(menu.String()), nil
		},
	)
	// [END streaming]

	// [START invoke-streaming]
	menuSuggestionFlow.Stream(
		context.Background(),
		"French",
	)(func(sfv *core.StreamFlowValue[OutputType, StreamType], err error) bool {
		if err != nil {
			// handle err
			return false
		}
		if !sfv.Done {
			fmt.Print(sfv.Stream)
			return true
		} else {
			fmt.Print(sfv.Output)
			return false
		}
	})
	// [END invoke-streaming]
}

func makeStructuredMenuItemSuggestion(string) MenuSuggestion { return MenuSuggestion{} }

func makeFullMenuSuggestion(restaurantTheme InputType, menuChunks chan StreamType) {

}

// [START main]
func main() {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}
	genkit.DefineFlow(
		g,
		"menuSuggestionFlow",
		func(ctx context.Context, restaurantTheme string) (string, error) {
			// ...
			return "", nil
		},
	)
	<-ctx.Done()
}

// [END main]

func f4() {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	myFlow := genkit.DefineFlow(g, "myFlow", func(ctx context.Context, restaurantTheme string) (string, error) {
		return "", nil
	})

	// [START mux]
	mainMux := http.NewServeMux()
	mainMux.Handle("POST /flow/myFlow", genkit.Handler(myFlow))
	// [END mux]
	// [START run]
	genkit.DefineFlow(
		g,
		"menuSuggestionFlow",
		func(ctx context.Context, restaurantTheme string) (string, error) {
			themes, err := genkit.Run(ctx, "find-similar-themes", func() (string, error) {
				// ...
				return "", nil
			})

			// ...
			return themes, err
		})
	// [END run]

}

func deploy(ctx context.Context) {
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}
	_ = g
	// [START init]
	// TODO: Replace code snippet.
	// [END init]
}

func f5() {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}
	// [START auth]
	// TODO: Replace code snippet.
	// [END auth]
	_ = g
}

func f6() {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}
	_ = g
	// [START auth-create]
	// TODO: Replace code snippet.
	// [END auth-create]
	_ = err
	// [START auth-define]
	// TODO: Replace code snippet.
	// [END auth-define]
	// [START auth-run]
	// TODO: Replace code snippet.
	// [END auth-run]
	_ = err
}
