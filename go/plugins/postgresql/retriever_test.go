// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// You may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package postgresql

import (
	"context"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestRetriever_Fail_WrongTypeOfOption(t *testing.T) {
	ds := docStore{}
	res, err := ds.Retrieve(context.Background(), &ai.RetrieverRequest{Options: struct{}{}})
	require.Nil(t, res)
	require.Error(t, err)
	assert.ErrorContains(t, err, "postgres.Retrieve options have type")
}

func TestRetriever_Fail_EmbedReturnError(t *testing.T) {
	ds := docStore{
		config: &Config{Embedder: mockEmbedderFail{}},
	}
	res, err := ds.Retrieve(context.Background(), &ai.RetrieverRequest{})
	require.Nil(t, res)
	require.Error(t, err)
}
