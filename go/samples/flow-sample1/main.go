// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0


// This program can be manually tested like so:
// Start the server listening on port 3100:
//
//	go run . &
//
// Tell it to run a flow:
//
//	curl -d '{"data":{"key":"/flow/parent/parent", "input":{"start": {"input":null}}}}' http://localhost:3100/api/runAction
//
// In production mode (GENKIT_ENV missing or set to "prod"):
// Start the server listening on port 3400:
//
//	go run . &
//
// Tell it to run a flow:
//
// curl -d '{}' http://localhost:3400/parent

package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"strconv"

	"github.com/firebase/genkit/go/genkit"
)

func main() {
	g, err := genkit.New(nil)
	if err != nil {
		log.Fatalf("failed to create Genkit: %v", err)
	}

	basic := genkit.DefineFlow(g, "basic", func(ctx context.Context, subject string) (string, error) {
		foo, err := genkit.Run(ctx, "call-llm", func() (string, error) { return "subject: " + subject, nil })
		if err != nil {
			return "", err
		}
		return genkit.Run(ctx, "call-llm", func() (string, error) { return "foo: " + foo, nil })
	})

	auth := &testAuth{}

	genkit.DefineFlow(g, "withContext", func(ctx context.Context, subject string) (string, error) {
		authJson, err := json.Marshal(auth.FromContext(ctx))
		if err != nil {
			return "", err
		}

		return "subject=" + subject + ",auth=" + string(authJson), nil
	}, genkit.WithFlowAuth(auth))

	genkit.DefineFlow(g, "parent", func(ctx context.Context, _ struct{}) (string, error) {
		return basic.Run(ctx, "foo")
	})

	type complex struct {
		Key   string `json:"key"`
		Value int    `json:"value"`
	}

	genkit.DefineFlow(g, "complex", func(ctx context.Context, c complex) (string, error) {
		foo, err := genkit.Run(ctx, "call-llm", func() (string, error) { return c.Key + ": " + strconv.Itoa(c.Value), nil })
		if err != nil {
			return "", err
		}
		return foo, nil
	})

	genkit.DefineFlow(g, "throwy", func(ctx context.Context, err string) (string, error) {
		return "", errors.New(err)
	})

	type chunk struct {
		Count int `json:"count"`
	}

	genkit.DefineStreamingFlow(g, "streamy", func(ctx context.Context, count int, cb func(context.Context, chunk) error) (string, error) {
		i := 0
		if cb != nil {
			for ; i < count; i++ {
				if err := cb(ctx, chunk{i}); err != nil {
					return "", err
				}
			}
		}
		return fmt.Sprintf("done: %d, streamed: %d times", count, i), nil
	})

	genkit.DefineStreamingFlow(g, "streamyThrowy", func(ctx context.Context, count int, cb func(context.Context, chunk) error) (string, error) {
		i := 0
		if cb != nil {
			for ; i < count; i++ {
				if i == 3 {
					return "", errors.New("boom!")
				}
				if err := cb(ctx, chunk{i}); err != nil {
					return "", err
				}
			}
		}
		return fmt.Sprintf("done: %d, streamed: %d times", count, i), nil
	})

	if err := g.Start(context.Background(), nil); err != nil {
		log.Fatal(err)
	}
}

type testAuth struct {
	genkit.FlowAuth
}

const authKey = "testAuth"

// ProvideAuthContext provides auth context from an auth header and sets it on the context.
func (f *testAuth) ProvideAuthContext(ctx context.Context, authHeader string) (context.Context, error) {
	var context genkit.AuthContext
	context = map[string]any{
		"username": authHeader,
	}
	return f.NewContext(ctx, context), nil
}

// NewContext sets the auth context on the given context.
func (f *testAuth) NewContext(ctx context.Context, authContext genkit.AuthContext) context.Context {
	return context.WithValue(ctx, authKey, authContext)
}

// FromContext retrieves the auth context from the given context.
func (*testAuth) FromContext(ctx context.Context) genkit.AuthContext {
	if ctx == nil {
		return nil
	}
	val := ctx.Value(authKey)
	if val == nil {
		return nil
	}
	return val.(genkit.AuthContext)
}

// CheckAuthPolicy checks auth context against policy.
func (f *testAuth) CheckAuthPolicy(ctx context.Context, input any) error {
	authContext := f.FromContext(ctx)
	if authContext == nil {
		return errors.New("auth is required")
	}
	if authContext["username"] != "authorized" {
		return errors.New("unauthorized")
	}
	return nil
}
