// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package server

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
)

// Start starts a new HTTP server and manages its lifecycle.
// This is a convenience function since Go does not manage interrupt signals directly.
func Start(ctx context.Context, addr string, mux *http.ServeMux) error {
	ctx, cancel := signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)
	defer cancel()

	srv := &http.Server{
		Addr:    addr,
		Handler: mux,
	}

	errChan := make(chan error, 1)

	go func() {
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errChan <- fmt.Errorf("server error: %w", err)
		}
		cancel()
	}()

	select {
	case err := <-errChan:
		return err
	case <-ctx.Done():
		if err := srv.Shutdown(ctx); err != nil {
			return fmt.Errorf("failed to shutdown server: %w", err)
		}
	}
	return nil
}
