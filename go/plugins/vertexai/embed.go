// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package vertexai

import (
	"context"
	"fmt"
	"strings"

	aiplatform "cloud.google.com/go/aiplatform/apiv1"
	"cloud.google.com/go/aiplatform/apiv1/aiplatformpb"
	"github.com/firebase/genkit/go/ai"
	"google.golang.org/protobuf/types/known/structpb"
)

// EmbedOptions are options for the Vertex AI embedder.
// Set [ai.EmbedRequest.Options] to a value of type *[EmbedOptions].
type EmbedOptions struct {
	// Document title.
	Title string `json:"title,omitempty"`
	// Task type: RETRIEVAL_QUERY, RETRIEVAL_DOCUMENT, and so forth.
	// See the Vertex AI text embedding docs.
	TaskType string `json:"task_type,omitempty"`
}

func embed(ctx context.Context, reqEndpoint string, client *aiplatform.PredictionClient, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
	preq, err := newPredictRequest(reqEndpoint, req)
	if err != nil {
		return nil, err
	}
	resp, err := client.Predict(ctx, preq)
	if err != nil {
		return nil, err
	}

	if g, w := len(resp.Predictions), len(req.Documents); g != w {
		return nil, fmt.Errorf("vertexai: got %d embeddings, expected %d", g, w)
	}

	ret := &ai.EmbedResponse{}
	for _, pred := range resp.Predictions {
		values := pred.GetStructValue().Fields["embeddings"].GetStructValue().Fields["values"].GetListValue().Values
		vals := make([]float32, len(values))
		for i, value := range values {
			vals[i] = float32(value.GetNumberValue())
		}
		ret.Embeddings = append(ret.Embeddings, &ai.DocumentEmbedding{Embedding: vals})
	}
	return ret, nil
}

// newPredictRequest creates a PredictRequest from an EmbedRequest.
// Each Document in the EmbedRequest becomes a separate instance in the PredictRequest.
func newPredictRequest(endpoint string, req *ai.EmbedRequest) (*aiplatformpb.PredictRequest, error) {
	var title, taskType string
	if options, _ := req.Options.(*EmbedOptions); options != nil {
		title = options.Title
		taskType = options.TaskType
	}
	instances := make([]*structpb.Value, 0, len(req.Documents))
	for _, doc := range req.Documents {
		fields := map[string]any{
			"content": text(doc),
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

	return &aiplatformpb.PredictRequest{
		Endpoint:  endpoint,
		Instances: instances,
	}, nil
}

// text concatenates all the text parts of the document together,
// with no delimiter.
func text(d *ai.Document) string {
	var b strings.Builder
	for _, p := range d.Content {
		if p.IsText() {
			b.WriteString(p.Text)
		}
	}
	return b.String()
}
