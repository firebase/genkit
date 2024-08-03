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

	firebase "firebase.google.com/go/v4"
	"firebase.google.com/go/v4/auth"
	"github.com/firebase/genkit/go/genkit"
)

var (
	a *firebase.App
)

type firebaseAuth struct {
	client   *auth.Client                    // Firebase Auth client.
	policy   func(map[string]any, any) error // Auth policy to check against.
	required bool                            // Auth required even for direct calls.
}

// NewFirebaseAuth creates a Firebase auth check.
func NewFirebaseAuth(ctx context.Context, policy func(map[string]any, any) error, required bool) (genkit.FlowAuth, error) {
	app, err := app(ctx)
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

// ProvideAuthContext provides auth context from an auth header.
func (f *firebaseAuth) ProvideAuthContext(ctx context.Context, authHeader string) (map[string]any, error) {
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

	authBytes, err := json.Marshal(authToken)
	if err != nil {
		return nil, err
	}

	var authContext map[string]any
	if err = json.Unmarshal(authBytes, &authContext); err != nil {
		return nil, err
	}

	return authContext, nil
}

// CheckAuthPolicy checks auth context against policy.
func (f *firebaseAuth) CheckAuthPolicy(authContext map[string]any, input any) error {
	if authContext == nil {
		if f.required {
			return errors.New("auth is required")
		}
		return nil
	}
	return f.policy(authContext, input)
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
