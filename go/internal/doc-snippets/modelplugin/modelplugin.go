package modelplugin

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
)

const providerID = "mymodels"

// [START cfg]
type MyModelConfig struct {
	ai.GenerationCommonConfig
	CustomOption int
	AnotherCustomOption string
}
// [END cfg]

func Init() error {
	// [START definemodel]
	ai.DefineModel(
		providerID, "my-model",
		&ai.ModelMetadata{
			Label: "my-model",
			Supports: ai.ModelCapabilities{
				Multiturn:  true,  // Does the model support multi-turn chats?
				SystemRole: true,  // Does the model support syatem messages?
				Media:      false, // Can the model accept media input?
				Tools:      false, // Does the model support function calling (tools)?
			},
		},
		func(ctx context.Context,
			genRequest *ai.GenerateRequest,
			_ ai.ModelStreamingCallback,
		) (*ai.GenerateResponse, error) {
			// Verify that the request includes a configuration that conforms to
			// your schema .
			if _, ok := genRequest.Config.(MyModelConfig); !ok {
				return nil, fmt.Errorf("request config must be type MyModelConfig")
			}

			// Use your custom logic to convert Genkit's ai.GenerateRequest
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
			// ai.GenerateResponse.
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

func genResponseFromAPIResponse(apiResponse string) (*ai.GenerateResponse, error) {
	panic("unimplemented")
}

func callModelAPI(apiRequest string) (string, error) {
	panic("unimplemented")
}

func apiRequestFromGenkitRequest(genRequest *ai.GenerateRequest) (string, error) {
	panic("unimplemented")
}
