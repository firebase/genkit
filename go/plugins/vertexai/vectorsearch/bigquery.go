package vectorsearch

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"cloud.google.com/go/bigquery"
	"github.com/firebase/genkit/go/ai"
	"google.golang.org/api/iterator"
)

// BigQueryDocumentRow defines the structure of a row in the BigQuery table.
type BigQueryDocumentRow struct {
	ID       string `bigquery:"id"`
	Content  string `bigquery:"content"`  // Stored as JSON string
	Metadata string `bigquery:"metadata"` // Stored as JSON string
}

// GetBigQueryDocumentRetriever creates a BigQuery Document Retriever.
// This function returns a DocumentRetriever function that retrieves documents
// from a BigQuery table based on the provided neighbors' IDs.
func GetBigQueryDocumentRetriever(bqClient *bigquery.Client, projectID, datasetID, tableID string) DocumentRetriever {
	return func(ctx context.Context, neighbors []Neighbor, options any) ([]*ai.Document, error) {
		var ids []string
		for _, neighbor := range neighbors {
			if neighbor.DatapointID != "" {
				ids = append(ids, neighbor.DatapointID)
			}
		}

		if len(ids) == 0 {
			return []*ai.Document{}, nil
		}

		// Constructing the query with UNNEST for array parameters
		// BigQuery expects parameters for IN clauses with UNNEST to be arrays.
		query := fmt.Sprintf("SELECT id, content, metadata FROM `%s.%s.%s` WHERE id IN UNNEST(@ids)", projectID, datasetID, tableID)

		q := bqClient.Query(query)
		q.Parameters = []bigquery.QueryParameter{
			{Name: "ids", Value: ids},
		}

		it, err := q.Read(ctx)
		if err != nil {
			log.Printf("Failed to execute BigQuery query: %v", err)
			return nil, fmt.Errorf("failed to query BigQuery: %w", err)
		}

		var documents []*ai.Document
		for {
			var row BigQueryDocumentRow
			err := it.Next(&row)
			if err == iterator.Done {
				break
			}
			if err != nil {
				log.Printf("Error reading BigQuery row: %v", err)
				return nil, fmt.Errorf("error reading BigQuery row: %w", err)
			}

			var metadata map[string]any
			// Parse metadata if present
			if row.Metadata != "" {
				if err := json.Unmarshal([]byte(row.Metadata), &metadata); err != nil {
					log.Printf("Failed to parse metadata for document ID %s: %v", row.ID, err)
					// Continue even if metadata parsing fails, as content might still be valid
				}
			}

			doc := ai.DocumentFromText(row.Content, metadata)

			documents = append(documents, doc)
		}

		return documents, nil
	}
}
