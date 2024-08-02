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

package main

import (
	"context"
	"errors"
	"fmt"
	"log"

	"firebase.google.com/go/v4/auth"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/firebase"
)

func main() {
	ctx := context.Background()

	policy := func(authToken *auth.Token, user string) error {
		if authToken == nil || authToken.UID != user {
			return errors.New("user ID does not match")
		}
		return nil
	}

	firebaseAuth, err := firebase.NewFirebaseAuth(ctx, policy, true)
	if err != nil {
		log.Fatalf("failed to set up Firebase auth: %v", err)
	}

	flowWithRequiredAuth := genkit.DefineFlow("flow-with-required-auth", func(ctx context.Context, user string) (string, error) {
		return fmt.Sprintf("secret about user %s", user), nil
	}, genkit.WithFlowAuth(firebaseAuth))

	firebaseAuth, err = firebase.NewFirebaseAuth(ctx, policy, false)
	if err != nil {
		log.Fatalf("failed to set up Firebase auth: %v", err)
	}

	flowWithAuth := genkit.DefineFlow("flow-with-auth", func(ctx context.Context, user string) (string, error) {
		return fmt.Sprintf("secret about user %s", user), nil
	}, genkit.WithFlowAuth(firebaseAuth))

	genkit.DefineFlow("super-caller", func(ctx context.Context, _ struct{}) (string, error) {
		resp1, err := flowWithRequiredAuth.Run(ctx, "admin-user", genkit.WithLocalAuth(&auth.Token{UID: "admin-user"}))
		if err != nil {
			return "", fmt.Errorf("flowWithRequiredAuth: %w", err)
		}
		resp2, err := flowWithAuth.Run(ctx, "admin-user-2")
		if err != nil {
			return "", fmt.Errorf("flowWithAuth: %w", err)
		}
		return resp1 + ", " + resp2, nil
	}, genkit.NoAuth[struct{}]())

	if err := genkit.Init(context.Background(), nil); err != nil {
		log.Fatal(err)
	}
}
