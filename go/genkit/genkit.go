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

// Package genkit provides Genkit functionality for application developers.
package genkit

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"

	"github.com/firebase/genkit/go/internal/common"
	"github.com/firebase/genkit/go/internal/registry"
)

// Options are options to [Init].
type Options struct {
	// If "-", do not start a FlowServer.
	// Otherwise, start a FlowServer on the given address, or the
	// default of ":3400" if empty.
	FlowAddr string
	// The names of flows to serve.
	// If empty, all registered flows are served.
	Flows []string
}

// Init initializes Genkit.
// After it is called, no further actions can be defined.
//
// Init starts servers depending on the value of the GENKIT_ENV
// environment variable and the provided options.
//
// If GENKIT_ENV = "dev", a development server is started
// in a separate goroutine at the address in opts.DevAddr, or the default
// of ":3100" if empty.
//
// If opts.FlowAddr is a value other than "-", a flow server is started (see [StartFlowServer])
// and the call to Init waits for the server to shut down.
// If opts.FlowAddr == "-", no flow server is started and Init returns immediately.
//
// Thus Init(nil) will start a dev server in the "dev" environment, will always start
// a flow server, and will pause execution until the flow server terminates.
func Init(ctx context.Context, opts *Options) error {
	if opts == nil {
		opts = &Options{}
	}
	registry.Global.Freeze()

	var mu sync.Mutex
	var servers []*http.Server
	var wg sync.WaitGroup
	errCh := make(chan error, 2)

	if common.CurrentEnvironment() == common.EnvironmentDev {
		wg.Add(1)
		go func() {
			defer wg.Done()
			s := startReflectionServer(errCh)
			mu.Lock()
			servers = append(servers, s)
			mu.Unlock()
		}()
	}

	if opts.FlowAddr != "-" {
		wg.Add(1)
		go func() {
			defer wg.Done()
			s := startFlowServer(opts.FlowAddr, opts.Flows, errCh)
			mu.Lock()
			servers = append(servers, s)
			mu.Unlock()
		}()
	}

	serverStartCh := make(chan struct{})
	go func() {
		wg.Wait()
		close(serverStartCh)
	}()

	// It will block here until either all servers start up or there is an error in starting one.
	select {
	case <-serverStartCh:
		slog.Info("all servers started successfully")
	case err := <-errCh:
		return fmt.Errorf("failed to start servers: %w", err)
	case <-ctx.Done():
		return ctx.Err()
	}

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGINT, syscall.SIGTERM)

	// It will block here (i.e. servers will run) until we get an interrupt signal.
	select {
	case sig := <-sigCh:
		slog.Info("received signal, initiating shutdown", "signal", sig)
	case err := <-errCh:
		slog.Error("server error", "err", err)
		return err
	case <-ctx.Done():
		slog.Info("context cancelled, initiating shutdown")
	}

	return shutdownServers(servers)
}
