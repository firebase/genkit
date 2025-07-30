package vectorsearch

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"golang.org/x/oauth2/google"
)

// IndexParams represents the parameters required for indexing.
type IndexParams struct {
	Docs            []*ai.Document
	Embedder        ai.Embedder
	EmbedderOptions any
	ProjectID       string
	Location        string
	IndexID         string
}

// DocumentRetriever defines the interface for retrieving documents.
type DocumentRetriever func(ctx context.Context, neighbors []Neighbor, options any) ([]*ai.Document, error)

// DocumentIndexer defines the interface for indexing documents.
type DocumentIndexer func(ctx context.Context, docs []*ai.Document) ([]string, error)

// RetrieveParams represents the parameters required for retrieving documents.
type RetrieveParams struct {
	Content           *ai.Document
	Embedder          ai.Embedder
	EmbedderOptions   any
	AuthClient        *google.Credentials
	ProjectNumber     string
	Location          string
	IndexEndpointID   string
	PublicDomainName  string
	DeployedIndexID   string
	NeighborCount     int
	Restricts         []Restrict
	NumericRestricts  []NumericRestrict
	DocumentRetriever DocumentRetriever `json:"-"` // Exclude from JSON serialization
}

// IIndexDatapoint represents the structure of a datapoint.
type IIndexDatapoint struct {
	DatapointID      string            `json:"datapoint_id"`
	FeatureVector    []float32         `json:"feature_vector"`
	Restricts        []Restrict        `json:"restricts,omitempty"`
	NumericRestricts []NumericRestrict `json:"numeric_restricts,omitempty"`
	CrowdingTag      string            `json:"crowding_tag,omitempty"`
}

// UpsertDatapointsParams represents the parameters required to upsert datapoints.
type UpsertDatapointsParams struct {
	Datapoints []IIndexDatapoint
	ProjectID  string
	Location   string
	IndexID    string
}

type Config struct {
	IndexID string
}

// Restrict represents a restriction for a datapoint.
type Restrict struct {
	Namespace string   `json:"namespace"`
	AllowList []string `json:"allowList,omitempty"`
	DenyList  []string `json:"denyList,omitempty"`
}

// NumericRestrict represents a numeric restriction for a datapoint.
type NumericRestrict struct {
	Namespace   string  `json:"namespace"`
	ValueFloat  float32 `json:"valueFloat,omitempty"`
	ValueInt    int64   `json:"valueInt,omitempty"`
	ValueDouble float64 `json:"valueDouble,omitempty"`
	Op          string  `json:"op,omitempty"`
}

type FindNeighborsResponse struct {
	NearestNeighbors []struct {
		Neighbors []Neighbor `json:"neighbors"`
	} `json:"nearestNeighbors"`
}

// Neighbor represents a single neighbor found by the vector search.
type Neighbor struct {
	Datapoint Datapoint `json:"datapoint"`
	Distance  float64   `json:"distance"`
}

type Datapoint struct {
	DatapointId      string            `json:"datapointId"`
	FeatureVector    []float32         `json:"featureVector"`
	Restricts        []Restrict        `json:"restricts,omitempty"`
	NumericRestricts []NumericRestrict `json:"numericRestricts,omitempty"`
	CrowdingTag      CrowdingAttribute `json:"crowdingTag,omitempty"`
}

type CrowdingAttribute struct {
	CrowdingAttribute string `json:"crowdingAttribute,omitempty"` // This field is optional
}

// FindNeighborsParams represents the parameters required to query the public endpoint.
type FindNeighborsParams struct {
	FeatureVector    []float32
	NeighborCount    int
	AuthClient       *google.Credentials
	ProjectNumber    string
	Location         string
	IndexEndpointID  string
	PublicDomainName string
	DeployedIndexID  string
	Restricts        []Restrict
	NumericRestricts []NumericRestrict
}
