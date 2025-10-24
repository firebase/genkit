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

package core

import (
	"context"
	"slices"
	"testing"

	"github.com/firebase/genkit/go/internal/registry"
)

func TestRunInFlow(t *testing.T) {
	r := registry.New()
	n := 0
	stepf := func() (int, error) {
		n++
		return n, nil
	}

	flow := DefineFlow(r, "run", func(ctx context.Context, _ any) ([]int, error) {
		g1, err := Run(ctx, "s1", stepf)
		if err != nil {
			return nil, err
		}
		g2, err := Run(ctx, "s2", stepf)
		if err != nil {
			return nil, err
		}
		return []int{g1, g2}, nil
	})
	got, err := flow.Run(context.Background(), nil)
	if err != nil {
		t.Fatal(err)
	}
	want := []int{1, 2}
	if !slices.Equal(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
}

func TestRunFlow(t *testing.T) {
	r := registry.New()
	f := DefineFlow(r, "inc", func(ctx context.Context, i int) (int, error) {
		return i + 1, nil
	})
	got, err := f.Run(context.Background(), 2)
	if err != nil {
		t.Fatal(err)
	}
	if want := 3; got != want {
		t.Errorf("got %d, want %d", got, want)
	}
}

func TestFlowNameFromContext(t *testing.T) {
	r := registry.New()
	flows := []*Flow[struct{}, string, struct{}]{
		DefineFlow(r, "DefineFlow", func(ctx context.Context, _ struct{}) (string, error) {
			return FlowNameFromContext(ctx), nil
		}),
		DefineStreamingFlow(r, "DefineStreamingFlow", func(ctx context.Context, _ struct{}, s StreamCallback[struct{}]) (string, error) {
			return FlowNameFromContext(ctx), nil
		}),
	}
	for _, flow := range flows {
		t.Run(flow.Name(), func(t *testing.T) {
			got, err := flow.Run(context.Background(), struct{}{})
			if err != nil {
				t.Fatal(err)
			}
			if want := flow.Name(); got != want {
				t.Errorf("got '%s', want '%s'", got, want)
			}
		})
	}
}