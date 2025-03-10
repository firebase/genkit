// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package weaviate

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strings"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/weaviate/weaviate-go-client/v4/weaviate"
	"github.com/weaviate/weaviate-go-client/v4/weaviate/auth"
	"github.com/weaviate/weaviate-go-client/v4/weaviate/graphql"
	"github.com/weaviate/weaviate/entities/models"
)

// The provider used in the registry.
const provider = "weaviate"

// The metadata key used to hold document text.
const textKey = "text"

// The metadata key to hold document metadata.
const metadataKey = "metadata"

// state holds the current plugin state.
var state struct {
	mu          sync.Mutex
	initialized bool
	client      *weaviate.Client
}

// getClient returns the client stored in the state.
func getClient() *weaviate.Client {
	state.mu.Lock()
	defer state.mu.Unlock()
	return state.client
}

// ClientConfig passes configuration options to the plugin.
type ClientConfig struct {
	// The hostname:port to use to contact the Weaviate database.
	// If not set, the default is read from the WEAVIATE_URL environment variable.
	Addr string
	// The scheme to use to contact the Weaviate database.
	// Typically http or https.
	// If not set, the default is https.
	Scheme string
	// The API key to use with the Weaviate database.
	// If not set, the default is read from the WEAVIATE_API_KEY environment variable.
	APIKey string
}

// Init initializes the Weaviate plugin.
// The cfg argument may be nil to use the defaults.
// This returns the [*weaviate.Client] in case it is useful,
// but many users will be able to use just [DefineIndexerAndRetriever].
func Init(ctx context.Context, cfg *ClientConfig) (*weaviate.Client, error) {
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initialized {
		panic("weaviate.Init already called")
	}

	var host string
	if cfg != nil {
		host = cfg.Addr
	}
	if host == "" {
		host = os.Getenv("WEAVIATE_URL")
	}

	var scheme string
	if cfg != nil {
		scheme = cfg.Scheme
	}
	if scheme == "" {
		scheme = "https"
	}

	var apiKey string
	if cfg != nil {
		apiKey = cfg.APIKey
	}
	if apiKey == "" {
		apiKey = os.Getenv("WEAVIATE_API_KEY")
	}

	config := weaviate.Config{
		Host:       host,
		Scheme:     scheme,
		AuthConfig: auth.ApiKey{Value: apiKey},
	}

	client, err := weaviate.NewClient(config)
	if err != nil {
		return nil, fmt.Errorf("weaviate initialization failed: %v", err)
	}

	live, err := client.Misc().LiveChecker().Do(ctx)
	if err != nil {
		return nil, fmt.Errorf("weaviate initialization failed: %v", err)
	}
	if !live {
		return nil, errors.New("weaviate instance not alive")
	}

	state.client = client
	state.initialized = true

	return client, nil
}

// ClassConfig holds configuration options for an indexer/retriever pair.
// Weaviate stores data in collections, and each collection has a class name.
// Use a separate genkit Indexer/Retriever for each different class.
type ClassConfig struct {
	// The weaviate class name. May not be the empty string.
	Class string

	// The Embedder and options to use to embed documents.
	// Embedder may not be nil.
	Embedder        ai.Embedder
	EmbedderOptions any
}

// DefineIndexerAndRetriever defines an [ai.Indexer] and [ai.Retriever]
// that use the same class.
// The name uniquely identifies the Indexer and Retriever
// in the registry.
func DefineIndexerAndRetriever(ctx context.Context, g *genkit.Genkit, cfg ClassConfig) (ai.Indexer, ai.Retriever, error) {
	if cfg.Embedder == nil {
		return nil, nil, errors.New("weaviate: Embedder required")
	}
	if cfg.Class == "" {
		return nil, nil, errors.New("weaviate: class required")
	}

	ds, err := newDocStore(ctx, &cfg)
	if err != nil {
		return nil, nil, err
	}
	indexer := genkit.DefineIndexer(g, provider, cfg.Class, ds.Index)
	retriever := genkit.DefineRetriever(g, provider, cfg.Class, ds.Retrieve)
	return indexer, retriever, nil
}

// docStore defines an Indexer and a Retriever.
type docStore struct {
	class           string
	embedder        ai.Embedder
	embedderOptions any
}

// newDocStore creates a docStore.
func newDocStore(ctx context.Context, cfg *ClassConfig) (*docStore, error) {
	client := getClient()
	if client == nil {
		return nil, errors.New("weaviate.Init not called")
	}

	// Create the class if it doesn't already exist.
	exists, err := client.Schema().ClassExistenceChecker().WithClassName(cfg.Class).Do(ctx)
	if err != nil {
		return nil, fmt.Errorf("weaviate class check failed for %q: %v", cfg.Class, err)
	}
	if !exists {
		cls := &models.Class{
			Class:      cfg.Class,
			Vectorizer: "none",
		}

		err := client.Schema().ClassCreator().WithClass(cls).Do(ctx)
		if err != nil {
			return nil, fmt.Errorf("failed to create weaviate class %q: %v", cfg.Class, err)
		}
	}

	ds := &docStore{
		class:           cfg.Class,
		embedder:        cfg.Embedder,
		embedderOptions: cfg.EmbedderOptions,
	}
	return ds, nil
}

// Indexer returns the indexer for the given class.
func Indexer(g *genkit.Genkit, class string) ai.Indexer {
	return genkit.LookupIndexer(g, provider, class)
}

// Retriever returns the retriever for the given class.
func Retriever(g *genkit.Genkit, class string) ai.Retriever {
	return genkit.LookupRetriever(g, provider, class)
}

// Index implements the genkit Retriever.Index method.
func (ds *docStore) Index(ctx context.Context, req *ai.IndexerRequest) error {
	if len(req.Documents) == 0 {
		return nil
	}

	// Use the embedder to convert each Document into a vector.
	ereq := &ai.EmbedRequest{
		Documents: req.Documents,
		Options:   ds.embedderOptions,
	}
	eres, err := ds.embedder.Embed(ctx, ereq)
	if err != nil {
		return fmt.Errorf("weaviate index embedding failed: %v", err)
	}

	objects := make([]*models.Object, 0, len(eres.Embeddings))
	for i, de := range eres.Embeddings {
		doc := req.Documents[i]

		var sb strings.Builder
		for _, p := range doc.Content {
			sb.WriteString(p.Text)
		}

		metadata := make(map[string]any)
		metadata[textKey] = sb.String()

		if doc.Metadata != nil {
			metadata[metadataKey] = doc.Metadata
		}

		obj := &models.Object{
			Class:      ds.class,
			Properties: metadata,
			Vector:     de.Embedding,
		}
		objects = append(objects, obj)
	}

	_, err = getClient().Batch().ObjectsBatcher().WithObjects(objects...).Do(ctx)
	if err != nil {
		return fmt.Errorf("weaviate insert failed: %v", err)
	}

	return nil
}

// RetrieverOptions may be passed in the Options field
// [ai.RetrieverRequest] to pass options to Weaviate.
// The options field should be either nil or
// a value of type *RetrieverOptions.
type RetrieverOptions struct {
	// Maximum number of values to retrieve.
	Count int `json:"count,omitempty"`
	// Keys to retrieve from document metadata.
	// There doesn't seem to be a way to ask for all of the metadata.
	MetadataKeys []string
}

// Retrieve implements the genkit Retriever.Retrieve method.
func (ds *docStore) Retrieve(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
	count := 3 // by default we fetch 3 documents
	var metadataKeys []string
	if req.Options != nil {
		ropt, ok := req.Options.(*RetrieverOptions)
		if !ok {
			return nil, fmt.Errorf("weaviate.Retrieve options have type %T, want %T", req.Options, &RetrieverOptions{})
		}
		count = ropt.Count
		metadataKeys = ropt.MetadataKeys
	}

	// Use the embedder to convert the document to a vector.
	ereq := &ai.EmbedRequest{
		Documents: []*ai.Document{req.Query},
		Options:   ds.embedderOptions,
	}
	eres, err := ds.embedder.Embed(ctx, ereq)
	if err != nil {
		return nil, fmt.Errorf("weaviate retrieve embedding failed: %v", err)
	}

	gql := getClient().GraphQL()
	fields := []graphql.Field{
		{Name: textKey},
	}
	if len(metadataKeys) > 0 {
		mfields := make([]graphql.Field, 0, len(metadataKeys))
		for _, k := range metadataKeys {
			mfields = append(mfields,
				graphql.Field{
					Name: k,
				},
			)
		}
		fields = append(fields,
			graphql.Field{
				Name:   metadataKey,
				Fields: mfields,
			},
		)
	}
	res, err := gql.Get().
		WithNearVector(
			gql.NearVectorArgBuilder().WithVector(eres.Embeddings[0].Embedding)).
		WithClassName(ds.class).
		WithFields(fields...).
		WithLimit(count).
		Do(ctx)
	if err != nil {
		return nil, fmt.Errorf("weaviate retrieve failed: %v", err)
	}
	if len(res.Errors) != 0 {
		ss := make([]string, 0, len(res.Errors))
		for _, e := range res.Errors {
			ss = append(ss, e.Message)
		}
		return nil, fmt.Errorf("weaviate retrieve failed: %v", ss)
	}

	data, ok := res.Data["Get"]
	if !ok {
		return nil, errors.New("weaviate retrieve did not return Get key")
	}

	doc, ok := data.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("weaviate retrieve returned type %T, expected %T", data, map[string]any{})
	}

	docValAny, ok := doc[ds.class]
	if !ok {
		return nil, fmt.Errorf("weaviate retrieve did not return %q key: %v", ds.class, doc)
	}
	docVal, ok := docValAny.([]any)
	if !ok {
		return nil, fmt.Errorf("weaviate retrieve returned document type %T, expected %T", docValAny, []any{})
	}

	var docs []*ai.Document
	for _, dv := range docVal {
		dvMap, ok := dv.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("weaviate retrieve doc has type %T, expected %T", dv, map[string]any{})
		}
		t, ok := dvMap[textKey]
		if !ok {
			return nil, fmt.Errorf("weaviate doc missing key %q", textKey)
		}
		s, ok := t.(string)
		if !ok {
			return nil, fmt.Errorf("weaviate text is type %T, want %T", t, "")
		}
		props, _ := dvMap[metadataKey].(map[string]any)

		d := ai.DocumentFromText(s, props)
		docs = append(docs, d)
	}

	ret := &ai.RetrieverResponse{
		Documents: docs,
	}
	return ret, nil
}
