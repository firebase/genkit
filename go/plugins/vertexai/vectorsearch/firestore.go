package vectorsearch

import (
	"context"
	"encoding/json"
	"log"

	"cloud.google.com/go/firestore"
	"github.com/firebase/genkit/go/ai" // Assuming this path for ai.Document
	// Potentially useful for other Firestore operations, though not directly used in current retrieval loop
)

// FirestoreDocumentData represents the structure of data as stored in Firestore.
type FirestoreDocumentData struct {
	Content  string         `firestore:"content"`
	Metadata map[string]any `firestore:"metadata,omitempty"`
}

// GetFirestoreDocumentRetriever creates a Firestore Document Retriever.
// This function returns a DocumentRetriever function that retrieves documents
// from a Firestore collection based on the provided Vertex AI Vector Search neighbors' IDs.
func GetFirestoreDocumentRetriever(db *firestore.Client, collectionName string) DocumentRetriever {
	return func(ctx context.Context, neighbors []Neighbor, options any) ([]*ai.Document, error) {
		docs := []*ai.Document{}
		for _, neighbor := range neighbors {
			if neighbor.DatapointID == "" {
				log.Printf("Skipping neighbor with empty or nil DatapointID: %+v", neighbor)
				continue
			}

			docRef := db.Collection(collectionName).Doc(neighbor.DatapointID)
			docSnapshot, err := docRef.Get(ctx)
			if err != nil {
				// Log the error but continue to try other neighbors.
				// If the error is specific (e.g., NotFound), you might handle it differently.
				log.Printf("Failed to get document %s from Firestore: %v", neighbor.DatapointID, err)
				continue
			}

			if !docSnapshot.Exists() {
				log.Printf("Document %s does not exist in collection %s. Skipping.", neighbor.DatapointID, collectionName)
				continue
			}

			var firestoreData FirestoreDocumentData
			if err := docSnapshot.DataTo(&firestoreData); err != nil {
				log.Printf("Failed to unmarshal document data for ID %s: %v", neighbor.DatapointID, err)
				continue
			}

			// Merge metadata: original metadata from Firestore + neighbor data.
			// The neighbor itself is added to metadata, matching JS behavior:
			// docData.metadata = { ...docData.metadata, ...neighbor };
			if firestoreData.Metadata == nil {
				firestoreData.Metadata = make(map[string]any)
			}
			// Use a map[string]any to represent the Neighbor struct for merging
			neighborMap := make(map[string]any)
			// Marshal and unmarshal neighbor to a map to handle nested struct if present
			neighborBytes, err := json.Marshal(neighbor)
			if err == nil {
				json.Unmarshal(neighborBytes, &neighborMap)
			} else {
				log.Printf("Warning: Failed to marshal neighbor to map for metadata merge: %v", err)
			}

			// Merge neighborMap into firestoreData.Metadata
			for k, v := range neighborMap {
				firestoreData.Metadata[k] = v
			}
			doc := ai.DocumentFromText(firestoreData.Content, firestoreData.Metadata)

			docs = append(docs, doc)
		}
		return docs, nil
	}
}
