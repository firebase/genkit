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
	AuthClient      *google.Credentials
	ProjectID       string
	Location        string
	IndexID         string
}

// DocumentRetriever defines the interface for retrieving documents.
type DocumentRetriever func(ctx context.Context, neighbors []Neighbor, options any) ([]*ai.Document, error)

// RetrieveParams represents the parameters required for retrieving documents.
type RetrieveParams struct {
	Content           *ai.Document
	Embedder          ai.Embedder
	EmbedderOptions   any
	AuthClient        *google.Credentials
	ProjectID         string
	Location          string
	IndexEndpointID   string
	PublicDomainName  string
	DeployedIndexID   string
	NeighborCount     int
	Restricts         []Restrict
	NumericRestricts  []NumericRestrict
	DocumentRetriever DocumentRetriever
}

// Neighbor represents a single neighbor returned by the FindNeighbors API.
type Neighbor struct {
	DatapointID   string    `json:"datapoint_id"`
	Distance      float64   `json:"distance"`
	FeatureVector []float64 `json:"feature_vector"`
}

// IIndexDatapoint represents the structure of a datapoint.
type IIndexDatapoint struct {
	DatapointID      string            `json:"datapoint_id"`
	FeatureVector    []float32         `json:"feature_vector"`
	Restricts        []Restrict        `json:"restricts,omitempty"`
	NumericRestricts []NumericRestrict `json:"numeric_restricts,omitempty"`
	CrowdingTag      string            `json:"crowding_tag,omitempty"`
}

// Restrict represents a restrict object.
type Restrict struct {
	Namespace string   `json:"namespace"`
	AllowList []string `json:"allow_list,omitempty"`
	DenyList  []string `json:"deny_list,omitempty"`
}

// NumericRestrict represents a numeric restrict object.
type NumericRestrict struct {
	Namespace   string   `json:"namespace"`
	ValueInt    *int     `json:"value_int,omitempty"`
	ValueFloat  *float32 `json:"value_float,omitempty"`
	ValueDouble *float64 `json:"value_double,omitempty"`
}

// UpsertDatapointsParams represents the parameters required to upsert datapoints.
type UpsertDatapointsParams struct {
	Datapoints []IIndexDatapoint
	AuthClient *google.Credentials
	ProjectID  string
	Location   string
	IndexID    string
}

type Config struct {
	IndexID string
}
