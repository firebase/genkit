// Copyright 2025 Google LLC
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

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/logger"
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
	if err != nil {
		log.Fatalf("could not start operation: %v", err)
	}

	// Get the background model for status checking
	bgAction := genkit.LookupBackgroundModel(g, "googleai", "veo-2.0-generate-001")
	if bgAction == nil {
		log.Fatalf("background model not found")
	}

	// Wait for operation to complete
	currentOp := resp
	for {
		// Check if operation completed with error
		if currentOp.Error != "" {
			log.Fatalf("operation failed: %s", currentOp.Error)
		}

		// Check if operation is complete
		if currentOp.Done {
			break
		}

		log.Printf("Operation %s is still running...", currentOp.ID)

		// Wait before polling again (avoid busy waiting)
		select {
		case <-ctx.Done():
			logger.FromContext(ctx).Debug("Context cancelled, stopping operation polling", "operationId", currentOp.ID)
			log.Fatalf("context cancelled: %v", ctx.Err())
		case <-time.After(2 * time.Second): // Poll every 2 seconds
		}

		// Check operation status
		updatedOp, err := bgAction.Check(ctx, currentOp)
		if err != nil {
			log.Fatalf("failed to check operation status: %v", err)
		}

		currentOp = updatedOp
	}

	// Operation completed, return the final result
	if currentOp != nil {
		opJson, _ := json.Marshal(currentOp.Output)
		fmt.Printf("%s", opJson)
	}
}
