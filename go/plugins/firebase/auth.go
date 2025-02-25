// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package firebase

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"firebase.google.com/go/v4/auth"
	"github.com/firebase/genkit/go/core"
)

// AuthContext is the context of an authenticated request.
type AuthContext = *auth.Token

// AuthPolicy is a function that validates an incoming request.
type AuthPolicy = func(context.Context, AuthContext, json.RawMessage) error

// AuthClient is a client for the Firebase Auth service.
type AuthClient interface {
	VerifyIDToken(context.Context, string) (*auth.Token, error)
}

// ContextProvider creates a Firebase context provider for Genkit actions.
func ContextProvider(ctx context.Context, policy AuthPolicy) (core.ContextProvider, error) {
	app, err := App(ctx)
	if err != nil {
		return nil, err
	}

	client, err := app.Auth(ctx)
	if err != nil {
		return nil, err
	}

	return func(ctx context.Context, input core.RequestData) (core.ActionContext, error) {
		authHeader, ok := input.Headers["authorization"]
		if !ok {
			return nil, errors.New("authorization header is required but not provided")
		}

		const bearerPrefix = "bearer "

		if !strings.HasPrefix(strings.ToLower(authHeader), bearerPrefix) {
			return nil, errors.New("invalid authorization header format")
		}

		token := authHeader[len(bearerPrefix):]
		authCtx, err := client.VerifyIDToken(ctx, token)
		if err != nil {
			return nil, fmt.Errorf("error verifying ID token: %v", err)
		}

		if policy != nil {
			if err := policy(ctx, authCtx, input.Input); err != nil {
				return nil, err
			}
		}

		return core.ActionContext{
			"auth": authCtx,
		}, nil
	}, nil
}
