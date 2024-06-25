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

package snippets

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"strings"

	"github.com/firebase/genkit/go/genkit"
)

func f1() {
	// !+flow1
	menuSuggestionFlow := genkit.DefineFlow(
		"menuSuggestionFlow",
		func(ctx context.Context, restaurantTheme string) (string, error) {
			suggestion := makeMenuItemSuggestion(restaurantTheme)
			return suggestion, nil
		})
	// !-flow1
	_ = menuSuggestionFlow

}

// !+msug
type MenuSuggestion struct {
	ItemName    string `json:"item_name"`
	Description string `json:"description"`
	Calories    int    `json:"calories"`
}

// !-msug

func makeMenuItemSuggestion(string) string { return "" }

func f2() {
	// !+flow2
	menuSuggestionFlow := genkit.DefineFlow(
		"menuSuggestionFlow",
		func(ctx context.Context, restaurantTheme string) (MenuSuggestion, error) {
			suggestion := makeStructuredMenuItemSuggestion(restaurantTheme)
			return suggestion, nil
		},
	)
	// !-flow2
	// !+run1
	suggestion, err := genkit.RunFlow(context.Background(), menuSuggestionFlow, "French")
	// !-run1
	_ = suggestion
	_ = err
}

// !+streaming-types
// Types for illustrative purposes.
type InputType string
type OutputType string
type StreamType string

//!-streaming-types

func f3() {
	// !+streaming
	menuSuggestionFlow := genkit.DefineStreamingFlow(
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
	// !-streaming

	// !+invoke-streaming
	genkit.StreamFlow(
		context.Background(),
		menuSuggestionFlow,
		"French",
	)(func(sfv *genkit.StreamFlowValue[OutputType, StreamType], err error) bool {
		if !sfv.Done {
			fmt.Print(sfv.Output)
			return true
		} else {
			return false
		}
	})
	// !-invoke-streaming
}

func makeStructuredMenuItemSuggestion(string) MenuSuggestion { return MenuSuggestion{} }

func makeFullMenuSuggestion(restaurantTheme InputType, menuChunks chan StreamType) {

}

// !+main
func main() {
	genkit.DefineFlow(
		"menuSuggestionFlow",
		func(ctx context.Context, restaurantTheme string) (string, error) {
			// ...
			return "", nil
		},
	)
	// StartFlowServer always returns a non-nil error: the one returned by
	// http.ListenAndServe.
	err := genkit.StartFlowServer(":1234", []string{})
	log.Fatal(err)
}

// !-main

func f4() {
	// !+mux
	mainMux := http.NewServeMux()
	mainMux.Handle("POST /flow/", http.StripPrefix("/flow/", genkit.NewFlowServeMux(nil)))
	// !-mux
	// !+run
	genkit.DefineFlow(
		"menuSuggestionFlow",
		func(ctx context.Context, restaurantTheme string) (string, error) {
			themes, err := genkit.Run(ctx, "find-similar-themes", func() (string, error) {
				// ...
				return "", nil
			})

			// ...
			return themes, err
		})
	// !-run

}
