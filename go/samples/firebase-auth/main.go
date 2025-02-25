// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"context"
	"fmt"
	"log"
	"net/http"

	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/firebase"
	"github.com/firebase/genkit/go/plugins/server"
)

func main() {
	ctx := context.Background()

	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatalf("failed to create Genkit: %v", err)
	}

	genkit.DefineFlow(g, "flow-with-auth", func(ctx context.Context, user string) (string, error) {
		return fmt.Sprintf("authenticated info about user %q", user), nil
	})

	ctxProvider, err := firebase.ContextProvider(ctx, nil)
	if err != nil {
		log.Fatalf("failed to create Firebase context provider: %v", err)
	}

	mux := http.NewServeMux()
	for _, a := range genkit.ListFlows(g) {
		mux.HandleFunc("POST /"+a.Name(), genkit.Handler(a, genkit.WithContextProviders(ctxProvider)))
	}
	log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
}
