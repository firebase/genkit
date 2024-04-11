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

// Package pinecone implements a genkit plugin for the Pinecone vector
// database. This defines an indexer and a retriever.
//
// Accessing Pinecone requires an API key, which is passed as an argument
// to the relevant functions. Passing the API key as the empty string
// directs this package to use the PINECONE_API_KEY environment variable.
//
// All Pinecone data is stored in what Pinecone calls an index.
// An index may be serverless, meaning that it scales based on usage,
// or it may be pod-based, meaning that it uses a specified hardware
// configuration (which Pinecone calls a pod).
// Each index has an associated host URL.
// Storing and retrieving data requires passing this URL.
// The URL may be retrieved using the Indexes or IndexData function;
// it's the Host field in the returned struct.
//
// Indexes can be partitioned into namespaces.
// Operations that use indexes pass a namespace argument,
// where the empty string represents the default namespace.
package pinecone

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
)

// Set pineconeDebug to true to dump data sent to and received from the server.
const pineconeDebug = false

// apiServer is the Pinecone API server.
const apiServer = "api.pinecone.io"

// Environment variables to use for configuration parameters.
const (
	apiKeyEnv = "PINECONE_API_KEY"
	hostEnv   = "PINECONE_CONTROLLER_HOST"
)

// A Client is used to perform database operations.
type Client struct {
	apiKey string
}

// NewClient builds a Client.
//
// apiKey is the API key to use to access Pinecone.
// If it is the empty string, it is read from the PINECONE_API_INDEX
// environment variable.
func NewClient(ctx context.Context, apiKey string) (*Client, error) {
	key, err := resolveAPIKey(apiKey)
	if err != nil {
		return nil, err
	}
	client := &Client{
		apiKey: key,
	}
	return client, nil
}

// An IndexData contains information about a single Pinecone index.
type IndexData struct {
	Name      string `json:"name"`      // index name
	Dimension int    `json:"dimension"` // dimension of vectors in index
	Host      string `json:"host"`      // index host name
	Metric    string `json:"metric"`    // index metric: euclidean, cosine, dotproduct
	Spec      struct {
		Pod        *Pod        `json:"pod,omitempty"`       // for pod-based indexes
		Serverless *Serverless `json:serverless,omitempty"` // for serverless indexes
	} `json:"spec"`
	Status struct {
		Ready bool   `json:"ready"` // whether the index is ready
		State string `json:"state"` // ready, etc.
	} `json:"status"`
}

// A Pod is information about a pod-based index.
// Pod-based indexes are associated with a set of hardware configurations.
type Pod struct {
	Environment      string       `json:"environment"` // index environment: hosting provider and region
	Metadata         *PodMetadata `json:metadata_config,omitempty"`
	Type             string       `json:"pod_type"`                    // pod type and size
	Pods             int          `json:"pods"`                        // number of pods in index
	Replicas         int          `json:"replicas"`                    // number of replicas
	Shards           int          `json:"shards"`                      // number of shards
	SourceCollection string       `json:"source_collection,omitempty"` // name of collection from which to create an index
}

// PodMetadata configures the metadata index.
type PodMetadata struct {
	Indexes []string `json:"indexes,omitempty"` // list of fields that should be indexed; nil for all
}

// A Serverless is information about a serverless index.
// Serverless indexes scale automatically with usage.
type Serverless struct {
	Cloud  string `json:"cloud"`  // Cloud name
	Region string `json:"region"` // Cloud region
}

// Indexes fetches the available indexes.
func (c *Client) Indexes(ctx context.Context) ([]IndexData, error) {
	var indexList struct {
		Indexes []IndexData `json:"indexes,omitempty"`
	}
	url := fmt.Sprintf("https://%s/indexes", apiServer)
	err := c.fetchData(ctx, url, &indexList)
	if err != nil {
		return nil, err
	}
	return indexList.Indexes, nil
}

// IndexData fetches the data for a specific index.
func (c *Client) IndexData(ctx context.Context, index string) (*IndexData, error) {
	var result IndexData
	url := fmt.Sprintf("https://%s/indexes/%s", apiServer, index)
	err := c.fetchData(ctx, url, &result)
	if err != nil {
		return nil, err
	}
	return &result, nil
}

// Index is used to access a specific Pinecone index.
type Index struct {
	client *Client
	host   string
}

// The Index method returns an [Index], used to access a specific
// Pinecone index.
//
// host is the controller host name. This implies which index to use.
// This comes from the [IndexData.Host] field of the [IndexData] struct
// describing the desired index.
// If it is the empty string, it is read from the PINECONE_CONTROLLER_HOST
// environment variable.
func (c *Client) Index(ctx context.Context, host string) (*Index, error) {
	h, err := resolveHost(host)
	if err != nil {
		return nil, err
	}
	index := &Index{
		client: c,
		host:   h,
	}
	return index, nil
}

// vectorData is the data that pinecone records for a single vector.
type vectorData struct {
	ID           string         `json:"id"`
	Values       []float32      `json:"values,omitempty"`
	SparseValues *SparseValues  `json:"sparse_values,omitempty"`
	Metadata     map[string]any `json:"metadata,omitempty"`
}

// Vector is a single vector stored in the index.
// Either Values or SparseValues should hold the actual data.
type Vector struct {
	ID           string         `json:"id"`                      // vector ID
	Values       []float32      `json:"values,omitempty"`        // vector values
	SparseValues *SparseValues  `json:"sparse_values,omitempty"` // sparse vector values
	Metadata     map[string]any `json:"metadata,omitempty"`      // associated metadata; may be nil
}

// SparseValues can be used if most values in a vector are zero.
// Instead of listing all the values in the vector,
// SparseValues uses two slices of the same length,
// such that the real vector can be constructed with
//
//	for i, ind := range sv.Indices {
//		v[ind] = Values[i]
//	}
type SparseValues struct {
	Indices []uint32  `json:"indices,omitempty"`
	Values  []float32 `json:"values,omitempty"`
}

// upsertData is the data written for an upsert request.
type upsertData struct {
	Vectors   []Vector `json:"vectors"`
	Namespace string   `json:"namespace,omitempty"`
}

// Upsert writes a set of vector records into the index.
// If a record ID already exists, the existing record is replaced
// with the new one.
// The namespace indicates which namespace to write to;
// an empty string means the default namespace.
//
// The Pinecone docs say that after an Upsert operation,
// the vectors may not be immediately visible.
// The Stats method will report whether the vectors can be seen.
func (idx *Index) Upsert(ctx context.Context, vectors []Vector, namespace string) error {
	url := fmt.Sprintf("https://%s/vectors/upsert", idx.host)
	data := upsertData{
		Vectors:   vectors,
		Namespace: namespace,
	}
	return idx.client.postData(ctx, url, &data, nil)
}

// queryData is the data written for a query request.
type queryData struct {
	Namespace       string         `json:"namespace,omitempty"`
	TopK            int            `json:"top_k,omitempty"`
	Filter          map[string]any `json:"filter,omitempty"`
	IncludeValues   bool           `json:"include_values,omitempty"`
	IncludeMetadata bool           `json:"include_metadata,omitempty"`
	Vector          []float32      `json:"vector,omitempty"`
	SparseVector    *SparseValues  `json:"sparse_vector,omitempty"`
	ID              string         `json:"id,omitempty"`
}

// WantData is a set of flags that indicates which information to return
// when looking up a vector in the database.
type WantData int

const (
	WantValues   WantData = 1 << iota // return values of matching vectors
	WantMetadata                      // return metadata of matching vectors
)

// QueryResult is a single vector returned by a Query operation.
type QueryResult struct {
	ID           string         `json:"id,omitempty"`
	Score        float32        `json:"score,omitempty"` // A higher score is more similar
	Values       []float32      `json:"values,omitempty"`
	SparseValues *SparseValues  `json:"sparse_values,omitempty"`
	Metadata     map[string]any `json:"metadata,omitempty"`
}

// queryResponse is the value returned by a Query operation.
type queryResponse struct {
	Matches   []*QueryResult `json:"matches,omitempty"`
	Namespace string         `json:"namespace,omitempty"`
	Usage     *usage         `json:"usage,omitempty"`
}

// usage is resources required for an operation.
type usage struct {
	ReadUnits int `json:"read_units,omitempty"`
}

// Query looks up a vector in the database.
// It returns a set of similar vectors.
// The count parameter is the maximum number of vectors to return.
func (idx *Index) Query(ctx context.Context, values []float32, count int, want WantData, namespace string) ([]*QueryResult, error) {
	url := fmt.Sprintf("https://%s/query", idx.host)
	data := queryData{
		Namespace:       namespace,
		TopK:            count,
		IncludeValues:   (want & WantValues) != 0,
		IncludeMetadata: (want & WantMetadata) != 0,
		Vector:          values,
	}
	var result queryResponse
	err := idx.client.postData(ctx, url, &data, &result)
	return result.Matches, err
}

// QueryByID looks up a vector in the database by ID.
func (idx *Index) QueryByID(ctx context.Context, id string, want WantData, namespace string) (*QueryResult, error) {
	url := fmt.Sprintf("https://%s/query", idx.host)
	data := queryData{
		Namespace:       namespace,
		TopK:            1,
		IncludeValues:   (want & WantValues) != 0,
		IncludeMetadata: (want & WantMetadata) != 0,
		ID:              id,
	}
	var result queryResponse
	if err := idx.client.postData(ctx, url, &data, &result); err != nil {
		return nil, err
	}
	if len(result.Matches) == 0 {
		return nil, nil
	}
	return result.Matches[0], nil
}

// deleteRequest is used for the delete operation.
type deleteRequest struct {
	IDs       []string       `json:"ids,omitempty"`        // vector IDs to delete
	DeleteAll bool           `json:"delete_all,omitempty"` // delete all vectors
	Namespace string         `json:"namespace,omitempty"`
	Filter    map[string]any `json:"filter,omitempty"` // delete vectors with matching metadata
}

// Delete deletes vectors from the database by ID.
func (idx *Index) DeleteByID(ctx context.Context, ids []string, namespace string) error {
	url := fmt.Sprintf("https://%s/vectors/delete", idx.host)
	data := &deleteRequest{
		IDs:       ids,
		Namespace: namespace,
	}
	return idx.client.postData(ctx, url, &data, nil)
}

// Stats is the data returns by the [Index.Stats] method.
type Stats struct {
	Dimension  int                        `json:"dimension,omitempty"`        // index dimension
	Fullness   float32                    `json:"indexFullness,omitempty"`    // fullness, only for pod-based indexes
	Count      int                        `json:"totalVectorCount,omitempty"` // number of vectors in index
	Namespaces map[string]*NamespaceStats `json:"namespaces,omitempty"`
}

// NamespaceStats is data returned by the [Index.Stats] method for a namespace.
type NamespaceStats struct {
	Count int `json:"vectorCount,omitempty"` // number of vectors in namespace
}

// Stats returns statistics about an index.
func (idx *Index) Stats(ctx context.Context) (*Stats, error) {
	url := fmt.Sprintf("https://%s/describe_index_stats", idx.host)
	var data struct {
		Filter map[string]any `json:"filter,omitempty"` // always empty for us
	}
	var result Stats
	if err := idx.client.postData(ctx, url, &data, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// fetchData fetches data from a Pinecone URL.
func (c *Client) fetchData(ctx context.Context, url string, result any) error {
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return err
	}
	req.Header.Add("Api-Key", c.apiKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return fmt.Errorf("pinecone request to %s failed: %v", url, err)
	}
	defer resp.Body.Close()

	if status := resp.StatusCode; status != http.StatusOK {
		if status == http.StatusUnauthorized {
			return errors.New("pinecone access unauthorized; possible incorrect API key")
		}
		return fmt.Errorf("pinecone request to %s received unexpected status code %v", url, status)
	}

	err = json.NewDecoder(resp.Body).Decode(result)
	if err != nil {
		return fmt.Errorf("pinecone unmarshaling failure from %s: %v", url, err)
	}

	return nil
}

// postData posts data to a Pinecone URL.
func (c *Client) postData(ctx context.Context, url string, post, result any) error {
	// bodyReader will be the body of the HTTP request.
	// httpWriter writes to the body of the HTTP request.
	bodyReader, httpWriter := io.Pipe()
	defer bodyReader.Close()

	req, err := http.NewRequestWithContext(ctx, "POST", url, bodyReader)
	if err != nil {
		return err
	}
	req.Header.Add("Api-Key", c.apiKey)
	req.Header.Add("Content-Type", "application/json")

	encode := func() error {
		if !pineconeDebug {
			enc := json.NewEncoder(httpWriter)
			if err := enc.Encode(post); err != nil {
				return err
			}
		} else {
			var buf bytes.Buffer
			enc := json.NewEncoder(&buf)
			if err := enc.Encode(post); err != nil {
				return err
			}
			b := buf.Bytes()
			fmt.Printf("pinecone: post to %s: %s\n", url, b)
			if _, err := httpWriter.Write(b); err != nil {
				return err
			}
		}

		if err := httpWriter.Close(); err != nil && err != io.ErrClosedPipe {
			return err
		}
		return nil
	}

	errch := make(chan error, 1)

	go func() {
		errch <- encode()
	}()

	// Passing req to Do promises that it will close the body,
	// in this case bodyReader. That will lead the goroutine to exit.
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return fmt.Errorf("pinecone post to %s failed: %v", url, err)
	}
	defer resp.Body.Close()

	// Check for an error encoding the posted data.
	if err := <-errch; err != nil {
		return fmt.Errorf("error encoding pinecone data posted to %s: %v", url, err)
	}

	if status := resp.StatusCode; status != http.StatusOK {
		serr := c.serverError(resp.Body)

		if status == http.StatusUnauthorized {
			return fmt.Errorf("pinecone access unauthorized: possible incorrect API key (%v)", serr)
		}
		return fmt.Errorf("pinecone post to %s received unexpected status code %v (%v)", url, status, serr)
	}

	var r io.Reader = resp.Body
	if pineconeDebug {
		data, err := io.ReadAll(resp.Body)
		if err != nil {
			return err
		}
		fmt.Printf("pinecone: reply from %s: %s\n", url, data)
		r = bytes.NewReader(data)
	}

	if result != nil {
		if err := json.NewDecoder(r).Decode(result); err != nil {
			return fmt.Errorf("unmarshaling result of post to %s failed: %v", url, err)
		}
	}

	return nil
}

// serverError does its best to read a Pinecone server error message
// out of an HTTP response.
func (c *Client) serverError(r io.Reader) error {
	errData, err := io.ReadAll(r)
	if err != nil {
		return fmt.Errorf("failed to read pinecone error response: %v", err)
	}

	var msg struct {
		Code    int      `json:"code"`
		Message string   `json:"message"`
		Details []string `json:"details,omitempty"`
	}
	err = json.Unmarshal(errData, &msg)
	if err != nil {
		return fmt.Errorf("failed to unmarshal pinecone error response %q: %v", errData, err)
	}
	if msg.Details != nil {
		return fmt.Errorf("pinecone error %d: %s %v", msg.Code, msg.Message, msg.Details)
	}
	return fmt.Errorf("pinecone error %d: %s", msg.Code, msg.Message)
}

// resolveAPIKey reads the API key from the environment if necessary.
func resolveAPIKey(apiKey string) (string, error) {
	if apiKey != "" {
		return apiKey, nil
	}
	key := os.Getenv(apiKeyEnv)
	if key == "" {
		return "", fmt.Errorf("pinecone API key not set; try setting %s", apiKeyEnv)
	}
	return key, nil
}

// resolveHost reads the host from the environment if necessary.
func resolveHost(host string) (string, error) {
	if host != "" {
		return host, nil
	}
	h := os.Getenv(hostEnv)
	if h == "" {
		return "", fmt.Errorf("pinecone controller host not set; try setting %s", hostEnv)
	}
	return h, nil
}
