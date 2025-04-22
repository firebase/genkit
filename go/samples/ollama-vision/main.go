package main

import (
	"context"
	"encoding/base64"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/ollama"
)

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

func main() {
	// Get the image path from command line argument or use a default path
	imagePath := "test.png"
	if len(os.Args) > 1 {
		imagePath = os.Args[1]
	}

	// Check if image exists
	if _, err := os.Stat(imagePath); os.IsNotExist(err) {
		log.Fatalf("Image file not found: %s", imagePath)
	}

	// Read the image file
	imageData, err := os.ReadFile(imagePath)
	if err != nil {
		log.Fatalf("Failed to read image file: %v", err)
	}

	// Detect content type (MIME type) from the file's binary signature
	contentType := http.DetectContentType(imageData)

	// If content type is generic/unknown, try to infer from file extension
	if contentType == "application/octet-stream" {
		contentType = getContentTypeFromExtension(imagePath)
	}

	// Encode image to base64
	base64Image := base64.StdEncoding.EncodeToString(imageData)
	dataURI := fmt.Sprintf("data:%s;base64,%s", contentType, base64Image)

	// Create a new Genkit instance
	g, err := genkit.Init(context.Background())
	if err != nil {
		log.Fatalf("Failed to initialize Genkit: %v", err)
	}

	// Initialize the Ollama plugin
	ollamaPlugin := &ollama.Ollama{
		ServerAddress: "http://localhost:11434", // Default Ollama server address
	}

	// Initialize the plugin
	err = ollamaPlugin.Init(context.Background(), g)
	if err != nil {
		log.Fatalf("Failed to initialize Ollama plugin: %v", err)
	}

	// Define a model that supports images (llava is one of the supported models)
	modelName := "llava"
	model := ollamaPlugin.DefineModel(g, ollama.ModelDefinition{
		Name: modelName,
		Type: "generate", // Using generate endpoint
	}, nil)

	// Create a context
	ctx := context.Background()

	// Create a request with text and image
	request := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					ai.NewTextPart("Describe what you see in this image:"),
					ai.NewMediaPart(contentType, dataURI),
				},
			},
		},
	}

	// Call the model
	fmt.Printf("Sending request to %s model...\n", modelName)
	response, err := model.Generate(ctx, request, nil)
	if err != nil {
		log.Fatalf("Error generating response: %v", err)
	}

	// Print the response
	fmt.Println("\nModel Response:")
	for _, part := range response.Message.Content {
		if part.IsText() {
			fmt.Println(part.Text)
		}
	}
}
