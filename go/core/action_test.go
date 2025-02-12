// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package core

import (
	"bytes"
	"context"
	"fmt"
	"slices"
	"testing"

	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/registry"
)

func inc(_ context.Context, x int, _ noStream) (int, error) {
	return x + 1, nil
}

func TestActionRun(t *testing.T) {
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
	a := defineAction(r, "test", "inc", atype.Custom, nil, nil, nil, inc)
	got, err := a.Run(context.Background(), 3, nil)
	if err != nil {
		t.Fatal(err)
	}
	if want := 4; got != want {
		t.Errorf("got %d, want %d", got, want)
	}
}

func TestActionRunJSON(t *testing.T) {
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
	a := defineAction(r, "test", "inc", atype.Custom, nil, nil, nil, inc)
	input := []byte("3")
	want := []byte("4")
	got, err := a.RunJSON(context.Background(), input, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
}

// count streams the numbers from 0 to n-1, then returns n.
func count(ctx context.Context, n int, cb func(context.Context, int) error) (int, error) {
	if cb != nil {
		for i := 0; i < n; i++ {
			if err := cb(ctx, i); err != nil {
				return 0, err
			}
		}
	}
	return n, nil
}

func TestActionStreaming(t *testing.T) {
	ctx := context.Background()
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
	a := defineAction(r, "test", "count", atype.Custom, nil, nil, nil, count)
	const n = 3

	// Non-streaming.
	got, err := a.Run(ctx, n, nil)
	if err != nil {
		t.Fatal(err)
	}
	if got != n {
		t.Fatalf("got %d, want %d", got, n)
	}

	// Streaming.
	var gotStreamed []int
	got, err = a.Run(ctx, n, func(_ context.Context, i int) error {
		gotStreamed = append(gotStreamed, i)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	wantStreamed := []int{0, 1, 2}
	if !slices.Equal(gotStreamed, wantStreamed) {
		t.Errorf("got %v, want %v", gotStreamed, wantStreamed)
	}
	if got != n {
		t.Errorf("got %d, want %d", got, n)
	}
}

func TestActionTracing(t *testing.T) {
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
	provider := "test"
	tc := tracing.NewTestOnlyTelemetryClient()
	r.TracingState().WriteTelemetryImmediate(tc)
	const actionName = "TestTracing-inc"
	a := defineAction(r, provider, actionName, atype.Custom, nil, nil, nil, inc)
	if _, err := a.Run(context.Background(), 3, nil); err != nil {
		t.Fatal(err)
	}
	// The same trace store is used for all tests, so there might be several traces.
	// Look for this one, which has a unique name.
	fullActionName := fmt.Sprintf("%s/%s", provider, actionName)
	for _, td := range tc.Traces {
		if td.DisplayName == fullActionName {
			// Spot check: expect a single span.
			if g, w := len(td.Spans), 1; g != w {
				t.Errorf("got %d spans, want %d", g, w)
			}
			return
		}
	}
	t.Fatalf("did not find trace named %q", actionName)
}

func countingMiddleware[In, Out, Stream any](counts *int) Middleware[In, Out, Stream] {
	return func(ctx context.Context, input In, cb func(context.Context, Stream) error, next Func[In, Out, Stream]) (Out, error) {
		*counts++
		return next(ctx, input, cb)
	}
}

func addOneMiddleware[Stream any](ctx context.Context, input int, cb func(context.Context, Stream) error, next Func[int, int, Stream]) (int, error) {
	return next(ctx, input+1, cb)
}

func multiplyOutputMiddleware[Stream any](ctx context.Context, input int, cb func(context.Context, Stream) error, next Func[int, int, Stream]) (int, error) {
	out, err := next(ctx, input, cb)
	if err != nil {
		return 0, err
	}
	return out * 2, nil
}

func doubleStreamMiddleware(ctx context.Context, input int, cb func(context.Context, int) error, next Func[int, int, int]) (int, error) {
	wrappedCb := func(ctx context.Context, val int) error {
		return cb(ctx, val*2)
	}
	return next(ctx, input, wrappedCb)
}

func TestMiddleware(t *testing.T) {
	ctx := context.Background()

	t.Run("Single middleware execution count", func(t *testing.T) {
		r, err := registry.New()
		if err != nil {
			t.Fatal(err)
		}

		counts := 0
		middleware := []Middleware[int, int, struct{}]{countingMiddleware[int, int, struct{}](&counts)}
		a := defineAction(r, "test", "inc", atype.Custom, nil, nil, middleware, inc)

		_, err = a.Run(ctx, 3, nil)
		if err != nil {
			t.Fatal(err)
		}

		if counts != 1 {
			t.Errorf("middleware execution count: got %d, want 1", counts)
		}
	})

	t.Run("Multiple middleware order", func(t *testing.T) {
		r, err := registry.New()
		if err != nil {
			t.Fatal(err)
		}

		middleware := []Middleware[int, int, struct{}]{
			addOneMiddleware[struct{}],
			multiplyOutputMiddleware[struct{}],
		}
		a := defineAction(r, "test", "inc", atype.Custom, nil, nil, middleware, inc)

		got, err := a.Run(ctx, 3, nil)
		if err != nil {
			t.Fatal(err)
		}

		want := 10
		if got != want {
			t.Errorf("got %d, want %d", got, want)
		}
	})

	t.Run("Streaming middleware", func(t *testing.T) {
		r, err := registry.New()
		if err != nil {
			t.Fatal(err)
		}

		middleware := []Middleware[int, int, int]{doubleStreamMiddleware}
		a := defineAction(r, "test", "count", atype.Custom, nil, nil, middleware, count)

		var gotStreamed []int
		got, err := a.Run(ctx, 3, func(_ context.Context, i int) error {
			gotStreamed = append(gotStreamed, i)
			return nil
		})
		if err != nil {
			t.Fatal(err)
		}

		wantStreamed := []int{0, 2, 4}
		if !slices.Equal(gotStreamed, wantStreamed) {
			t.Errorf("got streamed values %v, want %v", gotStreamed, wantStreamed)
		}
		if got != 3 {
			t.Errorf("got final value %d, want 3", got)
		}
	})

	t.Run("Error handling in middleware", func(t *testing.T) {
		r, err := registry.New()
		if err != nil {
			t.Fatal(err)
		}

		expectedErr := fmt.Errorf("middleware error")
		errorMiddleware := func(ctx context.Context, input int, cb func(context.Context, struct{}) error, next Func[int, int, struct{}]) (int, error) {
			return 0, expectedErr
		}

		middleware := []Middleware[int, int, struct{}]{errorMiddleware}
		a := defineAction(r, "test", "inc", atype.Custom, nil, nil, middleware, inc)

		_, err = a.Run(ctx, 3, nil)
		if err != expectedErr {
			t.Errorf("got error %v, want %v", err, expectedErr)
		}
	})

	t.Run("Context modification in middleware", func(t *testing.T) {
		r, err := registry.New()
		if err != nil {
			t.Fatal(err)
		}

		key := "test_key"
		value := "test_value"
		var gotValue string

		contextMiddleware := func(ctx context.Context, input int, cb func(context.Context, struct{}) error, next Func[int, int, struct{}]) (int, error) {
			newCtx := context.WithValue(ctx, key, value)
			return next(newCtx, input, cb)
		}

		checkContextMiddleware := func(ctx context.Context, input int, cb func(context.Context, struct{}) error, next Func[int, int, struct{}]) (int, error) {
			if v := ctx.Value(key); v != nil {
				gotValue = v.(string)
			}
			return next(ctx, input, cb)
		}

		middleware := []Middleware[int, int, struct{}]{contextMiddleware, checkContextMiddleware}
		a := defineAction(r, "test", "inc", atype.Custom, nil, nil, middleware, inc)

		_, err = a.Run(ctx, 3, nil)
		if err != nil {
			t.Fatal(err)
		}

		if gotValue != value {
			t.Errorf("got context value %q, want %q", gotValue, value)
		}
	})
}
