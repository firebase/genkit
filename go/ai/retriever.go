// Copyright 2025 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"errors"
	"fmt"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/registry"
)

// Retriever represents a document retriever.
type Retriever interface {
	// Name returns the name of the retriever.
	Name() string
	// Retrieve retrieves the documents.
	Retrieve(ctx context.Context, req *RetrieverRequest) (*RetrieverResponse, error)
}

// An retriever is used to retrieve documents from a database.
type retriever core.ActionDef[*RetrieverRequest, *RetrieverResponse, struct{}]

// DefineRetriever registers the given retrieve function as an action, and returns a
// [Retriever] that runs it.
func DefineRetriever(r *registry.Registry, provider, name string, ret func(context.Context, *RetrieverRequest) (*RetrieverResponse, error)) *retriever {
	return (*retriever)(core.DefineAction(r, provider, name, atype.Retriever, nil, ret))
}

// LookupRetriever looks up a [Retriever] registered by [DefineRetriever].
// It returns nil if the retriever was not defined.
func LookupRetriever(r *registry.Registry, provider, name string) Retriever {
	return (*retriever)(core.LookupActionFor[*RetrieverRequest, *RetrieverResponse, struct{}](r, atype.Retriever, provider, name))
}

// Retrieve runs the given [Retriever].
func (r *retriever) Retrieve(ctx context.Context, req *RetrieverRequest) (*RetrieverResponse, error) {
	if r == nil {
		return nil, errors.New("Retriever called on a nil Retriever; check that all retrievers are defined")
	}
	return (*core.ActionDef[*RetrieverRequest, *RetrieverResponse, struct{}])(r).Run(ctx, req, nil)
}

// Retrieve calls the retrivers with provided options.
func Retrieve(ctx context.Context, r Retriever, opts ...RetrieveOption) (*RetrieverResponse, error) {
	retOpts := &retrieveOptions{}
	for _, opt := range opts {
		if err := opt.applyRetrieve(retOpts); err != nil {
			return nil, fmt.Errorf("ai.Retrieve: error applying options: %w", err)
		}
	}

	if len(retOpts.Documents) > 1 {
		return nil, errors.New("ai.Retrieve: only supports a single document as input")
	}

	req := &RetrieverRequest{
		Query:   retOpts.Documents[0],
		Options: retOpts.Config,
	}

	return r.Retrieve(ctx, req)
}

func (r *retriever) Name() string {
	return (*core.ActionDef[*RetrieverRequest, *RetrieverResponse, struct{}])(r).Name()
}
