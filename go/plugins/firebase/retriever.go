// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// You may not use this file except in compliance with the License.
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
	"crypto/md5"
	"encoding/json"
	"fmt"
	"os"

	"cloud.google.com/go/firestore"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

type VectorType int

// Firestore collection environment variable key name
const firestoreCollection = "FIRESTORE_COLLECTION"

const (
	Vector64 VectorType = iota // Vector64 is the only supported vector type
)

// RetrieverOptions struct for retriever configuration
type RetrieverOptions struct {
	Name            string                    // Name of the retriever
	Label           string                    // Label for the retriever
	Collection      string                    // Firestore collection name
	Embedder        ai.Embedder               // Embedder instance for generating embeddings
	VectorField     string                    // Field name for storing vectors
	MetadataFields  []string                  // List of metadata fields to retrieve
	ContentField    string                    // Field name for storing content
	Limit           int                       // Limit on the number of results
	DistanceMeasure firestore.DistanceMeasure // Distance measure for vector similarity
	VectorType      VectorType                // Type of vector (e.g., Vector64)
}

// IndexOptions struct for indexer configuration
type IndexOptions struct {
	VectorType      VectorType  // Type of vector (e.g., Vector64)
	Name            string      // Name of the indexer
	Embedder        ai.Embedder // Embedder instance for generating embeddings
	EmbedderOptions any         // Options to pass to the embedder
	Collection      string      // Firestore collection name
}

// Convert a Firestore document snapshot to a Genkit Document object.
func convertToDoc(docSnapshots []*firestore.DocumentSnapshot, contentField string, metadataFields []string) []*ai.Document {
	var documents []*ai.Document // Prepare the documents to return in the response

	for _, result := range docSnapshots {
		data := result.Data() // Retrieve document data

		// Ensure content field exists and is of type string
		content, ok := data[contentField].(string)
		if !ok {
			fmt.Printf("Content field %s missing or not a string in document %s", contentField, result.Ref.ID)
			continue
		}

		// Extract metadata fields
		metadata := make(map[string]interface{})
		for _, field := range metadataFields {
			if value, ok := data[field]; ok {
				metadata[field] = value
			}
		}

		// Create a Genkit Document object
		doc := ai.DocumentFromText(content, metadata)
		documents = append(documents, doc)
	}
	return documents
}

// Convert a slice of float32 to a slice of float64
func convertToFloat64(queryEmbedding []float32) []float64 {
	queryEmbedding64 := make([]float64, len(queryEmbedding)) // Allocate memory for float64 slice
	for i, val := range queryEmbedding {
		queryEmbedding64[i] = float64(val) // Convert each element
	}
	return queryEmbedding64
}

// DefineFirestoreRetriever defines a retriever for Firestore
func DefineFirestoreRetriever(g *genkit.Genkit, cfg RetrieverOptions, client *firestore.Client) (ai.Retriever, error) {
	if cfg.VectorType != Vector64 {
		return nil, fmt.Errorf("DefineFirestoreRetriever: only Vector64 is supported")
	}
	if client == nil {
		return nil, fmt.Errorf("DefineFirestoreRetriever: Firestore client is not provided")
	}

	// Resolve the Firestore collection name
	collection, err := resolveFirestoreCollection(cfg.Collection)
	if err != nil {
		return nil, err
	}

	// Define the retriever function
	Retrieve := func(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
		if req.Query == nil {
			return nil, fmt.Errorf("DefineFirestoreRetriever: Request document is nil")
		}

		// Generate query embedding using the Embedder
		embedRequest := &ai.EmbedRequest{Input: []*ai.Document{req.Query}}
		embedResponse, err := cfg.Embedder.Embed(ctx, embedRequest)
		if err != nil {
			return nil, fmt.Errorf("DefineFirestoreRetriever: Embedding failed: %v", err)
		}

		if len(embedResponse.Embeddings) == 0 {
			return nil, fmt.Errorf("DefineFirestoreRetriever: No embeddings returned")
		}

		queryEmbedding := embedResponse.Embeddings[0].Embedding
		if len(queryEmbedding) == 0 {
			return nil, fmt.Errorf("DefineFirestoreRetriever: Generated embedding is empty")
		}

		// Perform the FindNearest query
		vectorQuery := client.Collection(collection).FindNearest(
			cfg.VectorField,
			firestore.Vector64(convertToFloat64(queryEmbedding)),
			cfg.Limit,
			cfg.DistanceMeasure,
			nil,
		)
		iter := vectorQuery.Documents(ctx)

		results, err := iter.GetAll()
		if err != nil {
			return nil, fmt.Errorf("DefineFirestoreRetriever: FindNearest query failed: %v", err)
		}

		// Convert Firestore documents to Genkit documents
		documents := convertToDoc(results, cfg.ContentField, cfg.MetadataFields)
		return &ai.RetrieverResponse{Documents: documents}, nil
	}

	// Register the retriever in Genkit
	return genkit.DefineRetriever(g, provider, cfg.Name, Retrieve), nil
}

// DefineFirestoreIndexer defines an indexer for Firestore
func DefineFirestoreIndexer(g *genkit.Genkit, cfg IndexOptions, client *firestore.Client) (ai.Indexer, error) {
	if cfg.VectorType != Vector64 {
		return nil, fmt.Errorf("DefineFirestoreIndexer: only Vector64 is supported")
	}
	if client == nil {
		return nil, fmt.Errorf("DefineFirestoreIndexer: Firestore client is not provided")
	}

	// Resolve the Firestore collection name
	collection, err := resolveFirestoreCollection(cfg.Collection)
	if err != nil {
		return nil, err
	}

	// Define the indexer function
	Index := func(ctx context.Context, req *ai.IndexerRequest) error {
		if len(req.Documents) == 0 {
			return fmt.Errorf("DefineFirestoreIndexer: Provide documents to index")
		}

		// Generate embeddings for the documents
		embedRequest := &ai.EmbedRequest{
			Input:   req.Documents,
			Options: cfg.EmbedderOptions,
		}
		embedResponse, err := cfg.Embedder.Embed(ctx, embedRequest)
		if err != nil {
			return fmt.Errorf("DefineFirestoreIndexer: Embedding failed: %v", err)
		}

		if len(embedResponse.Embeddings) == 0 {
			return fmt.Errorf("DefineFirestoreIndexer: No embeddings returned")
		}

		// Index each document in Firestore
		for i, docEmbed := range embedResponse.Embeddings {
			doc := req.Documents[i]
			id, err := docID(doc)
			if err != nil {
				return err
			}

			_, err = client.Collection(collection).Doc(id).Set(ctx, map[string]interface{}{
				"text":      doc.Content[0].Text,
				"embedding": firestore.Vector64(convertToFloat64(docEmbed.Embedding)),
				"metadata":  doc.Metadata,
			})
			if err != nil {
				return fmt.Errorf("failed to index document %d: %w", i+1, err)
			}
		}

		return nil
	}

	// Register the indexer in Genkit
	return genkit.DefineIndexer(g, provider, cfg.Name, Index), nil
}

// docID generates a unique ID for a document based on its content and metadata
func docID(doc *ai.Document) (string, error) {
	if doc.Metadata != nil {
		if id, ok := doc.Metadata["id"]; ok {
			return id.(string), nil
		}
	}
	b, err := json.Marshal(doc)
	if err != nil {
		return "", fmt.Errorf("pinecone: error marshaling document: %v", err)
	}
	return fmt.Sprintf("%02x", md5.Sum(b)), nil
}

// resolveFirestoreCollection resolves the Firestore collection name from the environment if necessary
func resolveFirestoreCollection(collectionName string) (string, error) {
	if collectionName != "" {
		return collectionName, nil
	}
	collectionName = os.Getenv(firestoreCollection)
	if collectionName == "" {
		return "", fmt.Errorf("firestore collection not set; try setting %s", firestoreCollection)
	}
	return collectionName, nil
}
