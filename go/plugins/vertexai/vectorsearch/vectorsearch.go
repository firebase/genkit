package vectorsearch

import (
	"context"
	"errors"
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

const (
	vectorsearchProvider = "vectorsearch"
)

type Vectorsearch struct {
	ProjectID string
	Location  string

	client  *client    // Client for the Vertex AI service.
	mu      sync.Mutex // Mutex to control access.
	initted bool
}

func (a *Vectorsearch) Name() string {
	return vectorsearchProvider
}

// Init initializes the VertexAI plugin and all known models and embedders.
// After calling Init, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func (v *Vectorsearch) Init(ctx context.Context, g *genkit.Genkit) (err error) {
	if v == nil {
		v = &Vectorsearch{}
	}
	v.mu.Lock()
	defer v.mu.Unlock()
	if v.initted {
		return errors.New("plugin already initialized")
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("Vectorsearch.Init: %w", err)
		}
	}()

	projectID := v.ProjectID
	if projectID == "" {
		projectID = os.Getenv("GOOGLE_CLOUD_PROJECT")
		if projectID == "" {
			return fmt.Errorf("Vertex AI requires setting GOOGLE_CLOUD_PROJECT in the environment. You can get a project ID at https://console.cloud.google.com/home/dashboard?project=%s", projectID)
		}
	}

	location := v.Location
	if location == "" {
		location = os.Getenv("GOOGLE_CLOUD_LOCATION")
		if location == "" {
			location = os.Getenv("GOOGLE_CLOUD_REGION")
		}
		if location == "" {
			return fmt.Errorf("Vertex AI requires setting GOOGLE_CLOUD_LOCATION or GOOGLE_CLOUD_REGION in the environment. You can get a location at https://cloud.google.com/vertex-ai/docs/general/locations")
		}
	}

	client, err := newClient(ctx)
	if err != nil {
		return err
	}
	v.client = client
	v.initted = true

	return nil
}

// DefineRetriever defines a Retriever with the given configuration.
func DefineRetriever(ctx context.Context, g *genkit.Genkit, cfg Config) (ai.Retriever, error) {
	v := genkit.LookupPlugin(g, vectorsearchProvider).(*Vectorsearch)
	if v == nil {
		return nil, errors.New("vectorsearch plugin not found; did you call genkit.Init with the pinecone plugin?")
	}

	return genkit.DefineRetriever(g, vectorsearchProvider, cfg.IndexID, v.Retrieve), nil
}

// Index indexes documents into a Vertex AI index.
func Index(ctx context.Context, g *genkit.Genkit, params IndexParams, documentIndexer DocumentIndexer) error {
	v := genkit.LookupPlugin(g, vectorsearchProvider).(*Vectorsearch)
	if len(params.Docs) == 0 {
		return nil
	}

	// Use the embedder to convert each Document into a vector.
	ereq := &ai.EmbedRequest{
		Input:   params.Docs,
		Options: params.EmbedderOptions,
	}
	eres, err := params.Embedder.Embed(ctx, ereq)
	if err != nil {
		return fmt.Errorf("pinecone index embedding failed: %v", err)
	}

	docIds, err := documentIndexer(ctx, params.Docs)
	if err != nil {
		return fmt.Errorf("error indexing documents: %v", err)
	}

	var datapoints []IIndexDatapoint
	for i, de := range eres.Embeddings {
		id := docIds[i]
		dp := IIndexDatapoint{
			DatapointID:   id,
			FeatureVector: de.Embedding,
		}
		if restricts, ok := params.Docs[i].Metadata["restricts"].([]Restrict); ok {
			dp.Restricts = restricts
		}
		if numericRestricts, ok := params.Docs[i].Metadata["numeric_restricts"].([]NumericRestrict); ok {
			dp.NumericRestricts = numericRestricts
		}
		if crowdingTag, ok := params.Docs[i].Metadata["crowding_tag"].(string); ok {
			dp.CrowdingTag = crowdingTag
		}
		datapoints = append(datapoints, dp)
	}

	// Upsert datapoints into the Vertex AI index.
	err = v.UpsertDatapoints(UpsertDatapointsParams{
		Datapoints: datapoints,
		ProjectID:  params.ProjectID,
		Location:   params.Location,
		IndexID:    params.IndexID,
	})
	if err != nil {
		return fmt.Errorf("error upserting datapoints: %v", err)
	}

	return nil
}

// Retrieve retrieves documents from a Vertex AI index based on a query.
func (v *Vectorsearch) Retrieve(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {

	params := req.Options.(*RetrieveParams)

	// Generate the embedding for the query content.
	embeddingReq := &ai.EmbedRequest{
		Input:   []*ai.Document{req.Query},
		Options: params.EmbedderOptions,
	}
	embeddingRes, err := params.Embedder.Embed(ctx, embeddingReq)
	if err != nil {
		return nil, fmt.Errorf("error generating embedding for query: %v", err)
	}
	if len(embeddingRes.Embeddings) == 0 {
		return nil, fmt.Errorf("no embeddings generated for query")
	}
	queryEmbedding := embeddingRes.Embeddings[0].Embedding

	// Query the public endpoint to find neighbors.
	findNeighborsParams := FindNeighborsParams{
		FeatureVector:    queryEmbedding,
		NeighborCount:    params.NeighborCount,
		ProjectNumber:    params.ProjectNumber,
		Location:         v.Location,
		IndexEndpointID:  params.IndexEndpointID,
		PublicDomainName: params.PublicDomainName,
		DeployedIndexID:  params.DeployedIndexID,
		Restricts:        params.Restricts,
		NumericRestricts: params.NumericRestricts,
	}
	findNeighborsRes, err := v.FindNeighbors(findNeighborsParams)
	if err != nil {
		return nil, fmt.Errorf("error querying public endpoint: %v", err)
	}

	// Extract neighbors from the response.
	if len(findNeighborsRes.NearestNeighbors[0].Neighbors) == 0 {
		return nil, nil // No neighbors found.
	}

	// Retrieve documents based on the neighbors.
	documentRetriever := params.DocumentRetriever
	documents, err := documentRetriever(ctx, findNeighborsRes.NearestNeighbors[0].Neighbors, nil)
	if err != nil {
		return nil, fmt.Errorf("error retrieving documents: %v", err)
	}

	return &ai.RetrieverResponse{
		Documents: documents,
	}, nil
}
