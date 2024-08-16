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

package firebase

import (
	"context"
	"flag"
	"fmt"
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

/*
	To run this test, you need to have a Firestore database set up and provide the necessary flags.

You will also need to have Application Default Credentials set up for Vertex AI
*/
func TestFirestoreRetriever(t *testing.T) {
	if *testProjectID == "" {
		t.Skip("skipping test because -test-project-id flag not used")
	}
	if *testCollection == "" {
		t.Skip("skipping test because -test-collection flag not used")
	}
	if *testVectorField == "" {
		t.Skip("skipping test because -test-vector-field flag not used")
	}
	ctx := context.Background()

	vertexAiConfig := vertexai.Config{
		ProjectID: *testProjectID,
		Location:  *testLocation,
	}

	err := vertexai.Init(ctx, &vertexAiConfig)
	if err != nil {
		t.Fatal(err)
	}

	testEmbedder := vertexai.Embedder("textembedding-gecko@003")

	if testEmbedder == nil {
		t.Fatal("embedder is nil")
	}

	pluginConfig := FirebasePluginConfig{
		ProjectID: *testProjectID,
	}

	Init(ctx, &pluginConfig)
	defer UnInit()

	client, err := firestore.NewClient(ctx, *testProjectID)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

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

	retriever, err := DefineFirestoreRetriever(retrieverConfig)
	if err != nil {
		t.Fatal(err)
	}

	testDocument := ai.DocumentFromText("Test document", map[string]any{"metadata": "test"})

	req := &ai.RetrieverRequest{
		Document: testDocument,
		Options:  RetrieverRequestOptions{Limit: 2, DistanceMeasure: firestore.DistanceMeasureEuclidean},
	}

	fmt.Print(&retriever, &req)

	resp, err := retriever.Retrieve(ctx, req)

	fmt.Print(&resp, &err)
	if err != nil {
		t.Fatal(err)
	}

	if resp == nil {
		t.Fatal("expected non-nil response, got nil")
	}

	if len(resp.Documents) != 2 {
		t.Errorf("expected 2 documents, got %d", len(resp.Documents))
	}

	for _, doc := range resp.Documents {
		if doc == nil {
			t.Error("retrieved document is nil")
		}
	}
	fmt.Printf("Doc with content \n\n %s \n\n retrieved \n\n", resp.Documents[0].Content[0].Text)
	fmt.Printf("Doc with content \n\n %s \n\n retrieved \n\n", resp.Documents[1].Content[0].Text)

}
