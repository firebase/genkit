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

package firebase

import (
	"context"
	"fmt"
	"testing"

	"github.com/firebase/genkit/go/genkit"
)

func TestFirestorePlugin(t *testing.T) {

	if *testProjectId == "" {
		t.Skip("skipping test because -test-project-id flag not used")
	}

	ctx := context.Background()

	Init(ctx, Config{
		ProjectId:   *testProjectId,
		ForceExport: true,
	})

	flow := genkit.DefineFlow("myFlow", func(ctx context.Context, s string) ([]int, error) {
		return []int{1, 2, 3}, nil
	})

	out, err := flow.Run(ctx, "")

	if err != nil {
		t.Fatal(err)
	}

	if len(out) != 3 {
		t.Fatalf("expected 3 results, got %d", len(out))
	}

	fmt.Println(out)

}
