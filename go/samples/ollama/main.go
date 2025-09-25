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
	"encoding/base64"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/ollama"
)

// WeatherInput defines the input structure for the weather tool
type WeatherInput struct {
	Location string `json:"location"`
}

// WeatherData represents weather information
type WeatherData struct {
	Location  string  `json:"location"`
	TempC     float64 `json:"temp_c"`
	TempF     float64 `json:"temp_f"`
	Condition string  `json:"condition"`
}

func main() {
	ctx := context.Background()

	// Initialize Genkit with the Ollama plugin
	ollamaPlugin := &ollama.Ollama{
		ServerAddress: "http://localhost:11434", // Default Ollama server address
		Timeout:       90,                       // Response timeout in seconds
	}

	g := genkit.Init(ctx, genkit.WithPlugins(ollamaPlugin))

	// Define tools
	weatherTool := genkit.DefineTool(g, "weather", "Get current weather for a location",
		func(ctx *ai.ToolContext, input WeatherInput) (WeatherData, error) {
			// Get weather data (simulated)
			return simulateWeather(input.Location), nil
		},
	)

	genkit.DefineFlow(g, "weather-tool", func(ctx context.Context, input any) (string, error) {
		// Define the Ollama model
		model := ollamaPlugin.DefineModel(g,
			ollama.ModelDefinition{
				Name: "llama3.1", // Choose an appropriate model
				Type: "chat",     // Must be chat for tool support
			},
			nil)

		// Create system message
		systemMsg := ai.NewSystemTextMessage(
			"You are a helpful assistant that can look up weather. " +
				"When providing weather information, use the appropriate tool.")

		// Create user message
		userMsg := ai.NewUserTextMessage("I'd like to know the weather in Tokyo.")

		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(model),
			ai.WithMessages(systemMsg, userMsg),
			ai.WithTools(weatherTool),
			ai.WithToolChoice(ai.ToolChoiceAuto),
		)
		if err != nil {
			return "", err
		}

		return resp.Text(), nil
	})

	genkit.DefineFlow(g, "vision", func(ctx context.Context, input any) (string, error) {
		// Define a model that supports images (llava is one of the supported models)
		model := ollamaPlugin.DefineModel(g, ollama.ModelDefinition{
			Name: "llava",
			Type: "generate",
		}, nil)

		imgData, err := readImage("test.png")
		if err != nil {
			return "", err
		}
		request := &ai.ModelRequest{
			Messages: []*ai.Message{
				{
					Role: ai.RoleUser,
					Content: []*ai.Part{
						ai.NewTextPart("Describe what you see in this image:"),
						ai.NewMediaPart(imgData.contentType, imgData.encodedData),
					},
				},
			},
		}

		resp, err := model.Generate(ctx, request, nil)
		if err != nil {
			return "", fmt.Errorf("error generating response: %w", err)
		}

		return resp.Text(), nil
	})

	<-ctx.Done()
}

// Helper functions

// simulateWeather returns simulated weather data for a location
func simulateWeather(location string) WeatherData {
	// In a real app, this would call a weather API
	// For demonstration, we'll return mock data
	tempC := 22.5
	switch location {
	case "Tokyo", "Tokyo, Japan":
		tempC = 24.0
	case "Paris", "Paris, France":
		tempC = 18.5
	case "New York", "New York, USA":
		tempC = 15.0
	}

	conditions := []string{"Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Stormy"}
	condition := conditions[time.Now().Unix()%int64(len(conditions))]

	return WeatherData{
		Location:  location,
		TempC:     tempC,
		TempF:     tempC*9/5 + 32,
		Condition: condition,
	}
}

type imageData struct {
	contentType string
	encodedData string
}

// reads an image and encodes its contents as a base64 string
func readImage(path string) (*imageData, error) {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return nil, fmt.Errorf("image not found: %w", err)
	}

	img, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read image file: %w", err)
	}

	contentType := http.DetectContentType(img)
	if contentType == "application/octet-stream" {
		contentType = getContentTypeFromExtension(path)
	}

	base64image := base64.StdEncoding.EncodeToString(img)
	dataURI := fmt.Sprintf("data:%s;base64,%s", contentType, base64image)

	return &imageData{
		contentType: contentType,
		encodedData: dataURI,
	}, nil
}

// getContentTypeFromExtension returns a MIME type based on file extension
func getContentTypeFromExtension(filename string) string {
	ext := strings.ToLower(filepath.Ext(filename))
	switch ext {
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".png":
		return "image/png"
	case ".gif":
		return "image/gif"
	case ".webp":
		return "image/webp"
	case ".bmp":
		return "image/bmp"
	case ".svg":
		return "image/svg+xml"
	default:
		return "image/png" // Default fallback
	}
}
