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
	"testing"

	"firebase.google.com/go/v4/auth"
)

type mockAuthClient struct {
	verifyIDTokenFunc func(context.Context, string) (*auth.Token, error)
}

func (m *mockAuthClient) VerifyIDToken(ctx context.Context, token string) (*auth.Token, error) {
	return m.verifyIDTokenFunc(ctx, token)
}

func TestProvideAuthContext(t *testing.T) {
	t.Parallel()

	ctx := context.Background()

	tests := []struct {
		name          string
		authHeader    string
		required      bool
		mockToken     *auth.Token
		mockError     error
		expectedUID   string
		expectedError string
	}{
		{
			name:       "Valid token",
			authHeader: "Bearer validtoken",
			required:   true,
			mockToken: &auth.Token{
				UID: "user123",
				Firebase: auth.FirebaseInfo{
					SignInProvider: "custom",
				},
			},
			mockError:     nil,
			expectedUID:   "user123",
			expectedError: "",
		},
		{
			name:          "Missing header when required",
			authHeader:    "",
			required:      true,
			expectedUID:   "",
			expectedError: "authorization header is required but not provided",
		},
		{
			name:          "Missing header when not required",
			authHeader:    "",
			required:      false,
			expectedUID:   "",
			expectedError: "",
		},
		{
			name:          "Invalid header format",
			authHeader:    "InvalidBearer token",
			required:      true,
			expectedUID:   "",
			expectedError: "invalid authorization header format",
		},
		{
			name:          "Token verification error",
			authHeader:    "Bearer invalidtoken",
			required:      true,
			mockToken:     nil,
			mockError:     errors.New("invalid token"),
			expectedUID:   "",
			expectedError: "error verifying ID token: invalid token",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			mockClient := &mockAuthClient{
				verifyIDTokenFunc: func(ctx context.Context, token string) (*auth.Token, error) {
					if token == "validtoken" {
						return tt.mockToken, tt.mockError
					}
					return nil, tt.mockError
				},
			}

			auth := &firebaseAuth{
				client:   mockClient,
				required: tt.required,
			}

			newCtx, err := auth.ProvideAuthContext(ctx, tt.authHeader)

			if tt.expectedError != "" {
				if err == nil || err.Error() != tt.expectedError {
					t.Errorf("Expected error %q, got %v", tt.expectedError, err)
				}
			} else if err != nil {
				t.Errorf("Unexpected error: %v", err)
			}

			if tt.expectedUID != "" {
				authContext := auth.FromContext(newCtx)
				if authContext == nil {
					t.Errorf("Expected non-nil auth context")
				} else {
					uid, ok := authContext["uid"].(string)
					if !ok {
						t.Errorf("Expected 'uid' to be a string, got %T", authContext["uid"])
					} else if uid != tt.expectedUID {
						t.Errorf("Expected UID %q, got %q", tt.expectedUID, uid)
					}
				}
			} else if auth.FromContext(newCtx) != nil && tt.authHeader != "" {
				t.Errorf("Expected nil auth context, but got non-nil")
			}
		})
	}
}

func TestCheckAuthPolicy(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name          string
		authContext   map[string]any
		input         any
		required      bool
		policy        func(map[string]any, any) error
		expectedError string
	}{
		{
			name:        "Valid auth context and policy",
			authContext: map[string]any{"uid": "user123"},
			input:       "test input",
			required:    true,
			policy: func(authContext map[string]any, in any) error {
				return nil
			},
			expectedError: "",
		},
		{
			name:        "Policy error",
			authContext: map[string]any{"uid": "user123"},
			input:       "test input",
			required:    true,
			policy: func(authContext map[string]any, in any) error {
				return errors.New("policy error")
			},
			expectedError: "policy error",
		},
		{
			name:          "Missing auth context when required",
			authContext:   nil,
			input:         "test input",
			required:      true,
			policy:        nil,
			expectedError: "auth is required",
		},
		{
			name:          "Missing auth context when not required",
			authContext:   nil,
			input:         "test input",
			required:      false,
			policy:        nil,
			expectedError: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			auth := &firebaseAuth{
				required: tt.required,
				policy:   tt.policy,
			}

			ctx := context.Background()
			if tt.authContext != nil {
				ctx = auth.NewContext(ctx, tt.authContext)
			}

			err := auth.CheckAuthPolicy(ctx, tt.input)

			if tt.expectedError != "" {
				if err == nil || err.Error() != tt.expectedError {
					t.Errorf("Expected error %q, got %v", tt.expectedError, err)
				}
			} else if err != nil {
				t.Errorf("Unexpected error: %v", err)
			}
		})
	}
}
