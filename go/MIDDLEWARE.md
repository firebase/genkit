# Genkit Middleware (Go)

Middleware in Genkit allows you to wrap your Flows (or any Action) with custom logic. This is useful for cross-cutting concerns like logging, authentication, validation, or modifying inputs/outputs.

Middleware is defined as a function that takes a `StreamingFunc` and returns a `StreamingFunc`.

## Defining Middleware

A middleware function typically follows this pattern:

```go
package main

import (
	"context"
	"log"

	"github.com/firebase/genkit/go/core"
)

func MyMiddleware[In, Out, Stream any](next core.StreamingFunc[In, Out, Stream]) core.StreamingFunc[In, Out, Stream] {
	return func(ctx context.Context, input In, cb func(context.Context, Stream) error) (Out, error) {
		// 1. Logic BEFORE the Flow runs
		// e.g., validate input, start timer, check auth

		// 2. Call the next handler in the chain
		output, err := next(ctx, input, cb)

		// 3. Logic AFTER the Flow runs
		// e.g., log success/failure, modify output

		return output, err
	}
}