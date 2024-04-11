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

package pinecone

import (
	"context"
	"flag"
	"slices"
	"testing"
	"time"
)

var (
	testAPIKey    = flag.String("test-pinecone-api-key", "", "Pinecone API key to use for tests")
	testIndex     = flag.String("test-pinecone-index", "", "Pinecone index to use for tests")
	testNamespace = flag.String("test-pinecone-namespace", "", "Pinecone namespace to use for tests")
)

func TestPinecone(t *testing.T) {
	if *testAPIKey == "" {
		t.Skip("skipping test because -test-pinecone-api-key flag not used")
	}
	if *testIndex == "" {
		t.Skip("skipping test because -test-pinecone-index flag not used")
	}

	// We use a different namespace for each test to avoid confusion.
	namespace := *testNamespace + "TestPinecone"

	ctx := context.Background()

	c, err := NewClient(ctx, *testAPIKey)
	if err != nil {
		t.Fatal(err)
	}

	indexData, err := c.IndexData(ctx, *testIndex)
	if err != nil {
		t.Fatal(err)
	}

	idx, err := c.Index(ctx, indexData.Host)

	// Make two very similar vectors and one different vector.

	v1 := make([]float32, indexData.Dimension)
	v2 := make([]float32, indexData.Dimension)
	v3 := make([]float32, indexData.Dimension)
	for i := range v1 {
		v1[i] = float32(i)
		v2[i] = float32(i)
		v3[i] = float32(indexData.Dimension - i)
	}
	v2[0] = 1

	vectors := []Vector{
		{
			ID:     "1",
			Values: v1,
		},
		{
			ID:     "2",
			Values: v2,
		},
		{
			ID:     "3",
			Values: v3,
		},
	}

	err = idx.Upsert(ctx, vectors, namespace)
	if err != nil {
		t.Fatal(err)
	}

	defer func() {
		if err := idx.DeleteByID(ctx, []string{"1", "2", "3"}, namespace); err != nil {
			t.Errorf("error deleting test vectors: %v", err)
		}
	}()

	// The Pinecone docs say that for stability we need to wait
	// until the vectors are visible. Tried using Stats but
	// it's unreliable because we don't know whether the test vectors
	// are already in the database due to an earlier failed test,
	// so we don't know what the number of vectors should be.
	wait := func() bool {
		delay := 10 * time.Millisecond
		for i := 0; i < 20; i++ {
			vec, err := idx.QueryByID(ctx, "1", 0, namespace)
			if err != nil {
				t.Fatal(err)
			}
			if vec != nil {
				// For some reason Pinecone doesn't
				// reliably return a vector with the same ID.
				switch vec.ID {
				case "1", "2", "3":
					return true
				}
			}
			time.Sleep(delay)
			delay *= 2
		}
		return false
	}
	if !wait() {
		t.Fatal("inserted records never became visible")
	}

	// Looking up v1 should return both v1 and v2.

	results, err := idx.Query(ctx, v1, 2, 0, namespace)
	if err != nil {
		t.Fatal(err)
	}
	if len(results) != 2 {
		t.Errorf("got %d results, expected 2", len(results))
	}
	var got []string
	for _, r := range results {
		t.Logf("ID %q has score %g", r.ID, r.Score)
		got = append(got, r.ID)
	}
	slices.Sort(got)
	want := []string{"1", "2"}
	if !slices.Equal(got, want) {
		t.Errorf("got IDs %v, expected %v", got, want)
	}
}
