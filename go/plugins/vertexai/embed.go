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

package vertexai

import (
	"context"
	"errors"
	"fmt"
	"runtime"

	aiplatform "cloud.google.com/go/aiplatform/apiv1"
	"cloud.google.com/go/aiplatform/apiv1/aiplatformpb"
	"github.com/firebase/genkit/go/ai"
	"google.golang.org/api/option"
	"google.golang.org/protobuf/types/known/structpb"
)

// embedder implements ai.Embedder.
type embedder struct {
	projectID string
	location  string
	model     string
	client    *aiplatform.PredictionClient
}

// EmbedOptions is options for the Vertex AI embedder.
// Set [ai.EmbedRequest].Options to a value of type &EmbedOptions.
type EmbedOptions struct {
	// Document title.
	Title string `json:"title,omitempty"`
	// Task type: RETRIEVAL_QUERY, RETRIEVAL_DOCUMENT, and so forth.
	// See the Vertex AI text embedding docs.
	TaskType string `json:"task_type,omitempty"`
}

// Embed converts a document to a multi-dimensional vector.
// This implements ai.Embedder.
func (e *embedder) Embed(ctx context.Context, req *ai.EmbedRequest) ([]float32, error) {
	var title, taskType string
	if options, _ := req.Options.(*EmbedOptions); options != nil {
		title = options.Title
		taskType = options.TaskType
	}

	endpoint := fmt.Sprintf("projects/%s/locations/%s/publishers/google/models/%s", e.projectID, e.location, e.model)

	instances := make([]*structpb.Value, 0, len(req.Document.Content))
	for _, part := range req.Document.Content {
		fields := map[string]any{
			"content": part.Text(),
		}
		if title != "" {
			fields["title"] = title
		}
		if taskType != "" {
			fields["task_type"] = taskType
		}
		str, err := structpb.NewStruct(fields)
		if err != nil {
			return nil, err
		}
		instance := structpb.NewStructValue(str)
		instances = append(instances, instance)
	}

	preq := &aiplatformpb.PredictRequest{
		Endpoint:  endpoint,
		Instances: instances,
	}
	resp, err := e.client.Predict(ctx, preq)
	if err != nil {
		return nil, err
	}

	// TODO(ianlancetaylor): This can return multiple vectors.
	// We just use the first one for now.

	if len(resp.Predictions) < 1 {
		return nil, errors.New("vertexai: embed request returned no values")
	}

	values := resp.Predictions[0].GetStructValue().Fields["embeddings"].GetStructValue().Fields["values"].GetListValue().Values
	ret := make([]float32, len(values))
	for i, value := range values {
		ret[i] = float32(value.GetNumberValue())
	}

	return ret, nil
}

// NewEmbedder returns an [ai.Embedder] that can compute the embedding
// of an input document.
func NewEmbedder(ctx context.Context, model, projectID, location string) (ai.Embedder, error) {
	endpoint := fmt.Sprintf("%s-aiplatform.googleapis.com:443", location)
	numConns := max(runtime.GOMAXPROCS(0), 4)
	o := []option.ClientOption{
		option.WithEndpoint(endpoint),
		option.WithGRPCConnectionPool(numConns),
	}

	client, err := aiplatform.NewPredictionClient(ctx, o...)
	if err != nil {
		return nil, err
	}
	embed := &embedder{
		projectID: projectID,
		location:  location,
		model:     model,
		client:    client,
	}
	return embed, nil
}
