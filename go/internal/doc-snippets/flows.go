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
	"errors"
	"fmt"
	"log"
	"net/http"
	"strings"

	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/firebase"
)

func f1() {
	// [START flow1]
	menuSuggestionFlow := genkit.DefineFlow(
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
	// [START flow2]
	menuSuggestionFlow := genkit.DefineFlow(
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
	// [START streaming]
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
	// [END streaming]

	// [START invoke-streaming]
	menuSuggestionFlow.Stream(
		context.Background(),
		"French",
	)(func(sfv *genkit.StreamFlowValue[OutputType, StreamType], err error) bool {
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
	genkit.DefineFlow(
		"menuSuggestionFlow",
		func(ctx context.Context, restaurantTheme string) (string, error) {
			// ...
			return "", nil
		},
	)
	if err := genkit.Init(context.Background(), nil); err != nil {
		log.Fatal(err)
	}
}

// [END main]

func f4() {
	// [START mux]
	mainMux := http.NewServeMux()
	mainMux.Handle("POST /flow/", http.StripPrefix("/flow/", genkit.NewFlowServeMux(nil)))
	// [END mux]
	// [START run]
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
	// [END run]

}

func deploy(ctx context.Context) {
	// [START init]
	if err := genkit.Init(ctx,
		&genkit.Options{FlowAddr: ":3400"}, // Add this parameter.
	); err != nil {
		log.Fatal(err)
	}
	// [END init]
}

func f5() {
	// [START auth]
	ctx := context.Background()
	// Define an auth policy and create a Firebase auth provider
	firebaseAuth, err := firebase.NewAuth(ctx, func(authContext genkit.AuthContext, input any) error {
		// The type must match the input type of the flow.
		userID := input.(string)
		if authContext == nil || authContext["UID"] != userID {
			return errors.New("user ID does not match")
		}
		return nil
	}, true)
	if err != nil {
		log.Fatalf("failed to set up Firebase auth: %v", err)
	}
	// Define a flow with authentication
	authenticatedFlow := genkit.DefineFlow(
		"authenticated-flow",
		func(ctx context.Context, userID string) (string, error) {
			return fmt.Sprintf("Secure data for user %s", userID), nil
		},
		genkit.WithFlowAuth(firebaseAuth),
	)
	// [END auth]
	_ = authenticatedFlow
}

func f6() {
	ctx := context.Background()
	var policy func(authContext genkit.AuthContext, input any) error
	required := true
	// [START auth-create]
	firebaseAuth, err := firebase.NewAuth(ctx, policy, required)
	// [END auth-create]
	_ = firebaseAuth
	_ = err
	userDataFunc := func(ctx context.Context, userID string) (string, error) {
		return fmt.Sprintf("Secure data for user %s", userID), nil
	}
	// [START auth-define]
	genkit.DefineFlow("secureUserFlow", userDataFunc, genkit.WithFlowAuth(firebaseAuth))
	// [END auth-define]
	authenticatedFlow := genkit.DefineFlow("your-flow", userDataFunc, genkit.WithFlowAuth(firebaseAuth))
	// [START auth-run]
	response, err := authenticatedFlow.Run(ctx, "user123",
		genkit.WithLocalAuth(map[string]any{"UID": "user123"}))
	// [END auth-run]
	_ = response
	_ = err
}
