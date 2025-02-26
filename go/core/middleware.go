// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package core

// Middleware is a function that wraps an action execution, similar to HTTP middleware.
// It can modify the input, output, and context, or perform side effects.
type Middleware[In, Out, Stream any] = func(StreamingFunc[In, Out, Stream]) StreamingFunc[In, Out, Stream]

// Middlewares returns an array of middlewares that are passes in as an argument.
// core.Middlewares(apple, banana) is identical to []core.Middleware[InputType, OutputType]{apple, banana}
func Middlewares[In, Out, Stream any](ms ...Middleware[In, Out, Stream]) []Middleware[In, Out, Stream] {
	return ms
}

// ChainMiddleware creates a new Middleware that applies a sequence of
// Middlewares, so that they execute in the given order when handling action
// request.
// In other words, ChainMiddleware(m1, m2)(handler) = m1(m2(handler))
func ChainMiddleware[In, Out, Stream any](middlewares ...Middleware[In, Out, Stream]) Middleware[In, Out, Stream] {
	return func(h StreamingFunc[In, Out, Stream]) StreamingFunc[In, Out, Stream] {
		for i := range middlewares {
			h = middlewares[len(middlewares)-1-i](h)
		}
		return h
	}
}
