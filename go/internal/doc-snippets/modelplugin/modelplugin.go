// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelplugin

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

const providerID = "mymodels"

// [START cfg]
type MyModelConfig struct {
	ai.GenerationCommonConfig
	CustomOption        int
	AnotherCustomOption string
}

// [END cfg]

func Init() error {
	g, err := genkit.New(nil)
	if err != nil {
		return err
	}

	// [START definemodel]
	genkit.DefineModel(g,
		providerID, "my-model",
		&ai.ModelInfo{
			Label: "my-model",
			Supports: &ai.ModelInfoSupports{
				Context:    false, // Default value set formally
				Multiturn:  true,  // Does the model support multi-turn chats?
				SystemRole: true,  // Does the model support syatem messages?
				Media:      false, // Can the model accept media input?
				Tools:      false, // Does the model support function calling (tools)?
			},
			Versions: make([]string, 0),
		},
		func(ctx context.Context,
			genRequest *ai.ModelRequest,
			_ ai.ModelStreamingCallback,
		) (*ai.ModelResponse, error) {
			// Verify that the request includes a configuration that conforms to
			// your schema .
			if _, ok := genRequest.Config.(MyModelConfig); !ok {
				return nil, fmt.Errorf("request config must be type MyModelConfig")
			}

			// Use your custom logic to convert Genkit's ai.ModelRequest
			// into a form usable by the model's native API.
			apiRequest, err := apiRequestFromGenkitRequest(genRequest)
			if err != nil {
				return nil, err
			}

			// Send the request to the model API, using your own code or the
			// model API's client library.
			apiResponse, err := callModelAPI(apiRequest)
			if err != nil {
				return nil, err
			}

			// Use your custom logic to convert the model's response to Genkin's
			// ai.ModelResponse.
			response, err := genResponseFromAPIResponse(apiResponse)
			if err != nil {
				return nil, err
			}

			return response, nil
		},
	)
	// [END definemodel]

	return nil
}

func genResponseFromAPIResponse(apiResponse string) (*ai.ModelResponse, error) {
	panic("unimplemented")
}

func callModelAPI(apiRequest string) (string, error) {
	panic("unimplemented")
}

func apiRequestFromGenkitRequest(genRequest *ai.ModelRequest) (string, error) {
	panic("unimplemented")
}
