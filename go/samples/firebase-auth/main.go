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

	firebaseAuth, err := firebase.NewFirebaseAuth(ctx, func(authToken *auth.Token, user string) error {
		if authToken.UID != user {
			return errors.New("user ID does not match")
		}
		return nil
	}, true)
	if err != nil {
		log.Fatalf("failed to set up Firebase auth: %v", err)
	}

	flowWithRequiredAuth := genkit.DefineFlow("flow-with-required-auth", func(ctx context.Context, user string) (string, error) {
		return fmt.Sprintf("secret about user %s", user), nil
	}, genkit.WithFlowAuth(firebaseAuth))

	firebaseAuth, err = firebase.NewFirebaseAuth(ctx, func(authToken *auth.Token, user string) error {
		if authToken.UID != user {
			return errors.New("user ID does not match")
		}
		return nil
	}, false)
	if err != nil {
		log.Fatalf("failed to set up Firebase auth: %v", err)
	}

	flowWithAuth := genkit.DefineFlow("flow-with-auth", func(ctx context.Context, user string) (string, error) {
		return fmt.Sprintf("secret about user %s", user), nil
	}, genkit.WithFlowAuth(firebaseAuth))

	genkit.DefineFlow("super-caller", func(ctx context.Context, _ struct{}) (string, error) {
		resp1, err := flowWithRequiredAuth.Run(ctx, "admin-user", genkit.WithLocalAuth(&auth.Token{UID: "admin-user"}))
		if err != nil {
			return "", err
		}
		resp2, err := flowWithAuth.Run(ctx, "admin-user-2")
		if err != nil {
			return "", err
		}
		return resp1 + ", " + resp2, nil
	}, genkit.NoAuth())

	if err := genkit.Init(context.Background(), nil); err != nil {
		log.Fatal(err)
	}
}
