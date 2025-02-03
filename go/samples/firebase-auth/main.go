// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0


package main

import (
	"context"
	"errors"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/firebase"
)

func main() {
	ctx := context.Background()

	g, err := genkit.New(nil)
	if err != nil {
		log.Fatalf("failed to create Genkit: %v", err)
	}

	policy := func(authContext genkit.AuthContext, input any) error {
		user := input.(string)
		if authContext == nil || authContext["UID"] != user {
			return errors.New("user ID does not match")
		}
		return nil
	}
	firebaseAuth, err := firebase.NewAuth(ctx, policy, true)
	if err != nil {
		log.Fatalf("failed to set up Firebase auth: %v", err)
	}

	flowWithRequiredAuth := genkit.DefineFlow(g, "flow-with-required-auth", func(ctx context.Context, user string) (string, error) {
		return fmt.Sprintf("info about user %q", user), nil
	}, genkit.WithFlowAuth(firebaseAuth))

	firebaseAuth, err = firebase.NewAuth(ctx, policy, false)
	if err != nil {
		log.Fatalf("failed to set up Firebase auth: %v", err)
	}

	flowWithAuth := genkit.DefineFlow(g, "flow-with-auth", func(ctx context.Context, user string) (string, error) {
		return fmt.Sprintf("info about user %q", user), nil
	}, genkit.WithFlowAuth(firebaseAuth))

	genkit.DefineFlow(g, "super-caller", func(ctx context.Context, _ struct{}) (string, error) {
		// Auth is required so we have to pass local credentials.
		resp1, err := flowWithRequiredAuth.Run(ctx, "admin-user", genkit.WithLocalAuth(map[string]any{"UID": "admin-user"}))
		if err != nil {
			return "", fmt.Errorf("flowWithRequiredAuth: %w", err)
		}
		// Auth is not required so we can just run the flow.
		resp2, err := flowWithAuth.Run(ctx, "admin-user-2")
		if err != nil {
			return "", fmt.Errorf("flowWithAuth: %w", err)
		}
		return resp1 + ", " + resp2, nil
	})

	if err := g.Start(ctx, nil); err != nil {
		log.Fatal(err)
	}
}
