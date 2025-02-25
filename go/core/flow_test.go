// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package core

import (
	"context"
	"slices"
	"testing"

	"github.com/firebase/genkit/go/internal/registry"
)

func TestRunInFlow(t *testing.T) {
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
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
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
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
