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
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"google.golang.org/genai"
)

func main() {
	ctx := context.Background()

	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

	operation, err := genkit.GenerateOperation(ctx, g,
		ai.WithMessages(ai.NewUserTextMessage("Cat racing mouse")),
		ai.WithModelName("googleai/veo-3.0-generate-001"),
		ai.WithConfig(&genai.GenerateVideosConfig{
			NumberOfVideos:  1,
			AspectRatio:     "16:9",
			DurationSeconds: genai.Ptr(int32(8)),
			Resolution:      "720p",
		}),
	)
	if err != nil {
		log.Fatalf("Failed to start video generation: %v", err)
	}

	log.Printf("Started operation: %s", operation.ID)
	printStatus(operation)

	operation, err = waitForCompletion(ctx, g, operation)
	if err != nil {
		log.Fatalf("Operation failed: %v", err)
	}

	log.Println("Video generation completed successfully!")

	if err := downloadGeneratedVideo(ctx, operation); err != nil {
		log.Fatalf("Failed to download video: %v", err)
	}

	log.Println("Video successfully downloaded to veo3_video.mp4")
}

// waitForCompletion polls the operation status until it completes.
func waitForCompletion(ctx context.Context, g *genkit.Genkit, op *core.Operation[*ai.ModelResponse]) (*core.Operation[*ai.ModelResponse], error) {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for !op.Done {
		select {
		case <-ctx.Done():
			return nil, fmt.Errorf("context cancelled: %w", ctx.Err())
		case <-ticker.C:
			updatedOp, err := genkit.CheckModelOperation(ctx, g, op)
			if err != nil {
				return nil, fmt.Errorf("failed to check status: %w", err)
			}

			if updatedOp.Error != nil {
				return nil, fmt.Errorf("operation error: %w", updatedOp.Error)
			}

			printStatus(updatedOp)
			op = updatedOp
		}
	}

	return op, nil
}

// printStatus prints the current status message from the operation.
func printStatus(op *core.Operation[*ai.ModelResponse]) {
	if op.Output != nil && op.Output.Message != nil && len(op.Output.Message.Content) > 0 {
		log.Printf("Status: %s", op.Output.Message.Content[0].Text)
	}
}

// downloadGeneratedVideo downloads the generated video from the operation result.
func downloadGeneratedVideo(ctx context.Context, operation *core.Operation[*ai.ModelResponse]) error {
	apiKey, err := getAPIKey()
	if err != nil {
		return err
	}

	videoURL, err := extractVideoURL(operation)
	if err != nil {
		return err
	}

	downloadURL := buildDownloadURL(videoURL, apiKey)

	return downloadVideo(ctx, downloadURL, "veo3_video.mp4")
}

// getAPIKey retrieves the API key from environment variables.
func getAPIKey() (string, error) {
	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		apiKey = os.Getenv("GOOGLE_API_KEY")
	}
	if apiKey == "" {
		return "", fmt.Errorf("no API key found. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
	}
	return apiKey, nil
}

// extractVideoURL extracts the video URL from the operation output.
func extractVideoURL(operation *core.Operation[*ai.ModelResponse]) (string, error) {
	if operation.Output == nil {
		return "", fmt.Errorf("operation output is nil")
	}

	if operation.Output.Message == nil {
		return "", fmt.Errorf("model response message is nil")
	}

	for _, part := range operation.Output.Message.Content {
		if part.IsMedia() && part.Text != "" {
			return part.Text, nil
		}
	}

	return "", fmt.Errorf("no video URL found in the operation output")
}

// buildDownloadURL appends the API key to the video URL if not already present.
func buildDownloadURL(videoURL, apiKey string) string {
	if strings.Contains(videoURL, "key=") {
		return videoURL
	}

	separator := "?"
	if strings.Contains(videoURL, "?") {
		separator = "&"
	}

	return fmt.Sprintf("%s%skey=%s", videoURL, separator, apiKey)
}

// downloadVideo downloads a file from a URL and saves it to the specified filename.
func downloadVideo(ctx context.Context, url, filename string) error {
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return fmt.Errorf("failed to create HTTP request: %w", err)
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to download video: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("failed to download video: HTTP %d", resp.StatusCode)
	}

	file, err := os.Create(filename)
	if err != nil {
		return fmt.Errorf("failed to create output file: %w", err)
	}
	defer file.Close()

	if _, err := io.Copy(file, resp.Body); err != nil {
		return fmt.Errorf("failed to write video data to file: %w", err)
	}

	return nil
}
