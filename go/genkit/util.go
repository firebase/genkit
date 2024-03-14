package genkit

import (
	"context"
)

// A contextKey is a unique, typed key for a value stored in a context.
type contextKey[T any] struct {
	key *int
}

func newContextKey[T any]() contextKey[T] {
	return contextKey[T]{key: new(int)}
}

// newContext returns ctx augmented with this key and the given value.
func (k contextKey[T]) newContext(ctx context.Context, value T) context.Context {
	return context.WithValue(ctx, k.key, value)
}

// fromContext returns the value associated with this key in the context,
// or the zero value for T if the key is not present.
func (k contextKey[T]) fromContext(ctx context.Context) T {
	t, _ := ctx.Value(k.key).(T)
	return t
}
