package firebase

import (
	"context"
	"flag"
	"fmt"
	"os"
	"testing"

	"cloud.google.com/go/firestore"
	"github.com/firebase/genkit/go/ai"
	vertexai "github.com/firebase/genkit/go/plugins/vertexai"
)

var (
	testProjectID   = flag.String("test-project-id", "", "GCP Project ID to use for tests")
	testCollection  = flag.String("test-collection", "", "Firestore collection to use for tests")
	testVectorField = flag.String("test-vector-field", "", "Firestore vector field to use for tests")
	testLocation    = flag.String("test-location", "us-central1", "Firestore location to use for tests")
)

func TestFirestoreRetriever(t *testing.T) {
	// Check if the required flags are set, otherwise skip the test
	if *testProjectID == "" {
		t.Skip("skipping test because -test-project-id flag not used")
	}
	if *testCollection == "" {
		t.Skip("skipping test because -test-collection flag not used")
	}
	if *testVectorField == "" {
		t.Skip("skipping test because -test-vector-field flag not used")
	}

	// Set environment variables for Firebase emulators
	os.Setenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
	os.Setenv("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")
	os.Setenv("FIREBASE_STORAGE_EMULATOR_HOST", "127.0.0.1:9199")
	os.Setenv("FIREBASE_DATABASE_EMULATOR_HOST", "127.0.0.1:9000")

	// Use context for initializing Firebase app and Vertex AI embedder
	ctx := context.Background()

	// Initialize Vertex AI configuration
	vertexAiConfig := vertexai.Config{
		ProjectID: *testProjectID,
		Location:  *testLocation,
	}
	err := vertexai.Init(ctx, &vertexAiConfig)
	if err != nil {
		t.Fatal(err)
	}

	// Get the embedder
	testEmbedder := vertexai.Embedder("textembedding-gecko@003")

	if testEmbedder == nil {
		t.Fatal("embedder is nil")
	}

	// Initialize Firebase plugin configuration
	pluginConfig := FirebasePluginConfig{
		ProjectID: *testProjectID,
	}

	// Initialize Firebase
	if err := Init(ctx, &pluginConfig); err != nil {
		t.Fatal(err)
	}
	defer unInit()

	// Create Firestore client
	client, err := firestore.NewClient(ctx, *testProjectID)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Set up test data in Firestore
	if err := setupTestCollection(ctx, client, *testCollection, *testVectorField, testEmbedder); err != nil {
		t.Fatalf("failed to set up test collection: %v", err)
	}

	// Define retriever configuration
	retrieverConfig := RetrieverOptions{
		Name:            "test-retriever",
		Label:           "Test Retriever",
		Client:          client,
		Embedder:        testEmbedder,
		Collection:      *testCollection,
		VectorField:     *testVectorField,
		ContentField:    "text",
		DistanceMeasure: firestore.DistanceMeasureEuclidean,
	}

	// Define the Firestore retriever
	retriever, err := DefineFirestoreRetriever(retrieverConfig)
	if err != nil {
		t.Fatal(err)
	}

	// Create a test document
	testDocument := ai.DocumentFromText("Test document", map[string]any{"metadata": "test"})

	// Create a retriever request
	req := &ai.RetrieverRequest{
		Document: testDocument,
		Options:  &RetrieverRequestOptions{Limit: 2, DistanceMeasure: firestore.DistanceMeasureEuclidean},
	}

	// Retrieve documents using the retriever
	resp, err := retriever.Retrieve(ctx, req)
	if err != nil {
		t.Fatal(err)
	}

	// Log and validate the response
	if resp == nil {
		t.Fatal("expected non-nil response, got nil")
	}
	t.Logf("Retrieved %d documents", len(resp.Documents))
	if len(resp.Documents) != 2 {
		t.Errorf("expected 2 documents, got %d", len(resp.Documents))
	}

	for _, doc := range resp.Documents {
		if doc == nil {
			t.Error("retrieved document is nil")
		}
	}
	t.Logf("Doc with content \n\n %s \n\n retrieved \n\n", resp.Documents[0].Content[0].Text)
	t.Logf("Doc with content \n\n %s \n\n retrieved \n\n", resp.Documents[1].Content[0].Text)
}

// setupTestCollection initializes a Firestore collection with sample documents.
func setupTestCollection(ctx context.Context, client *firestore.Client, collection string, vectorField string, embedder ai.Embedder) error {
	// Delete existing documents in the collection
	iter := client.Collection(collection).Documents(ctx)
	docs, err := iter.GetAll()
	if err != nil {
		return fmt.Errorf("failed to list documents for deletion: %v", err)
	}
	for _, doc := range docs {
		if _, err := doc.Ref.Delete(ctx); err != nil {
			return fmt.Errorf("failed to delete document %s: %v", doc.Ref.ID, err)
		}
	}

	// Add 10 sample documents with embeddings and text content
	for i := 0; i < 10; i++ {
		docID := fmt.Sprintf("doc-%d", i)
		text := fmt.Sprintf("This is test document number %d", i)

		doc := ai.DocumentFromText("Test document", map[string]any{"metadata": "test"}) // Create a document from text

		docs := []*ai.Document{doc}

		// Generate embedding for the text
		embedReq := &ai.EmbedRequest{
			Documents: docs,
		}
		embedResp, err := embedder.Embed(ctx, embedReq)
		if err != nil {
			return fmt.Errorf("failed to generate embedding for document %s: %v", docID, err)
		}

		data := map[string]interface{}{
			"text":      text,
			vectorField: embedResp.Embeddings[0].Embedding,
			"metadata": map[string]interface{}{
				"index": i,
			},
		}
		_, err = client.Collection(collection).Doc(docID).Set(ctx, data)
		if err != nil {
			return fmt.Errorf("failed to create document %s: %v", docID, err)
		}
	}
	return nil
}
