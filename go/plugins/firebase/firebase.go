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
	"errors"
	"fmt"
	"strings"

	firebase "firebase.google.com/go/v4"
	"firebase.google.com/go/v4/auth"
)

var (
	a *firebase.App
)

type firebaseAuth[In any] struct {
	client   *auth.Client                // Firebase Auth client.
	policy   func(*auth.Token, In) error // Auth policy to check against.
	required bool                        // Auth required even for direct calls.
}

// ProvideAuthContext provides auth context from an auth header.
func (f *firebaseAuth[In]) ProvideAuthContext(ctx context.Context, authHeader string) (*auth.Token, error) {
	if authHeader == "" {
		if f.required {
			return nil, errors.New("authorization header is required but not provided")
		}
		return nil, nil
	}

	const bearerPrefix = "bearer "
	if !strings.HasPrefix(strings.ToLower(authHeader), bearerPrefix) {
		return nil, errors.New("invalid authorization header format")
	}
	token := authHeader[len(bearerPrefix):]

	authToken, err := f.client.VerifyIDToken(ctx, token)
	if err != nil {
		return nil, fmt.Errorf("error verifying ID token: %v", err)
	}

	return authToken, nil
}

// CheckAuthPolicy checks auth context against policy.
func (f *firebaseAuth[In]) CheckAuthPolicy(authContext *auth.Token, input In) error {
	if f.required && authContext == nil {
		return errors.New("auth is required")
	}
	return f.policy(authContext, input)
}

// NewFirebaseAuth creates a Firebase auth check.
func NewFirebaseAuth[In, Out, Stream any](ctx context.Context, policy func(*auth.Token, In) error, required bool) (*firebaseAuth[In], error) {
	app, err := app(ctx)
	if err != nil {
		return nil, err
	}

	client, err := app.Auth(ctx)
	if err != nil {
		return nil, err
	}

	auth := &firebaseAuth[In]{
		client:   client,
		policy:   policy,
		required: required,
	}
	return auth, nil
}

// app returns a cached Firebase app.
func app(ctx context.Context) (*firebase.App, error) {
	if a == nil {
		app, err := firebase.NewApp(ctx, nil)
		if err != nil {
			return nil, err
		}
		a = app
	}
	return a, nil
}
