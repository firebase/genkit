// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0


package firebase

import (
	"context"
	"sync"

	firebase "firebase.google.com/go/v4"
	"firebase.google.com/go/v4/auth"
)

type FirebaseApp interface {
	Auth(ctx context.Context) (*auth.Client, error)
}

var (
	app   *firebase.App
	mutex sync.Mutex
)

// app returns a cached Firebase app.
func App(ctx context.Context) (FirebaseApp, error) {
	mutex.Lock()
	defer mutex.Unlock()
	if app == nil {
		newApp, err := firebase.NewApp(ctx, nil)
		if err != nil {
			return nil, err
		}
		app = newApp
	}
	return app, nil
}
