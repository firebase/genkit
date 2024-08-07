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
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"firebase.google.com/go/v4/auth"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal/base"
)

var authContextKey = base.NewContextKey[map[string]any]()

type AuthClient interface {
	VerifyIDToken(context.Context, string) (*auth.Token, error)
}

// firebaseAuth is a Firebase auth provider.
type firebaseAuth struct {
	client   AuthClient                      // Auth client for verifying ID tokens.
	policy   func(map[string]any, any) error // Auth policy for checking auth context.
	required bool                            // Whether auth is required for direct calls.
}

// NewAuth creates a Firebase auth check.
func NewAuth(ctx context.Context, policy func(map[string]any, any) error, required bool) (genkit.FlowAuth, error) {
	app, err := App(ctx)
	if err != nil {
		return nil, err
	}
	client, err := app.Auth(ctx)
	if err != nil {
		return nil, err
	}
	auth := &firebaseAuth{
		client:   client,
		policy:   policy,
		required: required,
	}
	return auth, nil
}

// ProvideAuthContext provides auth context from an auth header and sets it on the context.
func (f *firebaseAuth) ProvideAuthContext(ctx context.Context, authHeader string) (context.Context, error) {
	if authHeader == "" {
		if f.required {
			return nil, errors.New("authorization header is required but not provided")
		}
		return ctx, nil
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
	authBytes, err := json.Marshal(authToken)
	if err != nil {
		return nil, err
	}
	var authContext map[string]any
	if err = json.Unmarshal(authBytes, &authContext); err != nil {
		return nil, err
	}
	return f.NewContext(ctx, authContext), nil
}

// NewContext sets the auth context on the given context.
func (f *firebaseAuth) NewContext(ctx context.Context, authContext map[string]any) context.Context {
	if ctx == nil {
		return nil
	}
	return authContextKey.NewContext(ctx, authContext)
}

// FromContext retrieves the auth context from the given context.
func (*firebaseAuth) FromContext(ctx context.Context) map[string]any {
	if ctx == nil {
		return nil
	}
	return authContextKey.FromContext(ctx)
}

// CheckAuthPolicy checks auth context against policy.
func (f *firebaseAuth) CheckAuthPolicy(ctx context.Context, input any) error {
	authContext := f.FromContext(ctx)
	if authContext == nil {
		if f.required {
			return errors.New("auth is required")
		}
		return nil
	}
	return f.policy(authContext, input)
}
