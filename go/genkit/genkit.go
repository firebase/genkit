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
	"strings"
	"sync"
	"syscall"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/invopop/jsonschema"

	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// Genkit encapsulates a Genkit instance including the registry and configuration.
type Genkit struct {
	// The registry for this instance.
	reg *registry.Registry
	// Options to configure the instance.
	Opts *Options
}

type Options struct {
	// The default model to use if no model is specified.
	DefaultModel string
	// Directory where dotprompts are stored.
	PromptDir string
}

// StartOptions are options to [Start].
type StartOptions struct {
	// If "-", do not start a FlowServer.
	// Otherwise, start a FlowServer on the given address, or the
	// default of ":3400" if empty.
	FlowAddr string
	// The names of flows to serve.
	// If empty, all registered flows are served.
	Flows []string
}

// New creates a new Genkit instance.
func New(opts *Options) (*Genkit, error) {
	r, err := registry.New()
	if err != nil {
		return nil, err
	}
	if opts == nil {
		opts = &Options{}
	}
	parts := strings.Split(opts.DefaultModel, "/")
	if len(parts) != 2 {
		return nil, fmt.Errorf("invalid default model format %q, expected provider/name", opts.DefaultModel)
	}
	return &Genkit{
		reg:  r,
		Opts: opts,
	}, nil
}

// Start initializes Genkit.
// After it is called, no further actions can be defined.
//
// Start starts servers depending on the value of the GENKIT_ENV
// environment variable and the provided options.
//
// If GENKIT_ENV = "dev", a development server is started
// in a separate goroutine at the address in opts.DevAddr, or the default
// of ":3100" if empty.
//
// If opts.FlowAddr is a value other than "-", a flow server is started
// and the call to Start waits for the server to shut down.
// If opts.FlowAddr == "-", no flow server is started and Start returns immediately.
//
// Thus Start(nil) will start a dev server in the "dev" environment, will always start
// a flow server, and will pause execution until the flow server terminates.
func (g *Genkit) Start(ctx context.Context, opts *StartOptions) error {
	if opts == nil {
		opts = &StartOptions{}
	}
	g.reg.Freeze()

	var mu sync.Mutex
	var servers []*http.Server
	var wg sync.WaitGroup
	errCh := make(chan error, 2)

	if registry.CurrentEnvironment() == registry.EnvironmentDev {
		wg.Add(1)
		go func() {
			defer wg.Done()
			s := startReflectionServer(ctx, g.reg, errCh)
			mu.Lock()
			servers = append(servers, s)
			mu.Unlock()
		}()
	}

	if opts.FlowAddr != "-" {
		wg.Add(1)
		go func() {
			defer wg.Done()
			s := startFlowServer(g, opts.FlowAddr, opts.Flows, errCh)
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

// DefineModel registers the given generate function as an action, and returns a
// [Model] that runs it.
func DefineModel(
	g *Genkit,
	provider, name string,
	metadata *ai.ModelMetadata,
	generate func(context.Context, *ai.ModelRequest, ai.ModelStreamingCallback) (*ai.ModelResponse, error),
) ai.Model {
	return ai.DefineModel(g.reg, provider, name, metadata, generate)
}

// IsDefinedModel reports whether a model is defined.
func IsDefinedModel(g *Genkit, provider, name string) bool {
	return ai.IsDefinedModel(g.reg, provider, name)
}

// LookupModel looks up a [Model] registered by [DefineModel].
// It returns nil if the model was not defined.
func LookupModel(g *Genkit, provider, name string) ai.Model {
	return ai.LookupModel(g.reg, provider, name)
}

// DefineTool defines a tool to be passed to a model generate call.
func DefineTool[In, Out any](g *Genkit, name, description string, fn func(ctx context.Context, input In) (Out, error)) *ai.ToolDef[In, Out] {
	return ai.DefineTool(g.reg, name, description, fn)
}

// LookupTool looks up the tool in the registry by provided name and returns it.
func LookupTool(g *Genkit, name string) ai.Tool {
	return ai.LookupTool(g.reg, name)
}

// DefinePrompt takes a function that renders a prompt template
// into a [GenerateRequest] that may be passed to a [Model].
// The prompt expects some input described by inputSchema.
// DefinePrompt registers the function as an action,
// and returns a [Prompt] that runs it.
func DefinePrompt(
	g *Genkit,
	provider, name string,
	metadata map[string]any,
	inputSchema *jsonschema.Schema,
	render func(context.Context, any) (*ai.ModelRequest, error),
) *ai.Prompt {
	return ai.DefinePrompt(g.reg, provider, name, metadata, inputSchema, render)
}

// IsDefinedPrompt reports whether a [Prompt] is defined.
func IsDefinedPrompt(g *Genkit, provider, name string) bool {
	return ai.IsDefinedPrompt(g.reg, provider, name)
}

// LookupPrompt looks up a [Prompt] registered by [DefinePrompt].
// It returns nil if the prompt was not defined.
func LookupPrompt(g *Genkit, provider, name string) *ai.Prompt {
	return ai.LookupPrompt(g.reg, provider, name)
}

// Generate run generate request for this model. Returns ModelResponse struct.
func Generate(ctx context.Context, g *Genkit, opts ...ai.GenerateOption) (*ai.ModelResponse, error) {
	opts, err := optsWithDefaults(g, opts)
	if err != nil {
		return nil, err
	}
	return ai.Generate(ctx, g.reg, opts...)
}

// GenerateText run generate request for this model. Returns generated text only.
func GenerateText(ctx context.Context, g *Genkit, opts ...ai.GenerateOption) (string, error) {
	opts, err := optsWithDefaults(g, opts)
	if err != nil {
		return "", err
	}
	return ai.GenerateText(ctx, g.reg, opts...)
}

// GenerateData run generate request for this model. Returns ModelResponse struct and fills value with structured output.
func GenerateData(ctx context.Context, g *Genkit, value any, opts ...ai.GenerateOption) (*ai.ModelResponse, error) {
	opts, err := optsWithDefaults(g, opts)
	if err != nil {
		return nil, err
	}
	return ai.GenerateData(ctx, g.reg, value, opts...)
}

// GenerateWithRequest runs the model with the given request and streaming callback.
func GenerateWithRequest(ctx context.Context, g *Genkit, m ai.Model, req *ai.ModelRequest, cb ai.ModelStreamingCallback) (*ai.ModelResponse, error) {
	return m.Generate(ctx, g.reg, req, cb)
}

// DefineIndexer registers the given index function as an action, and returns an
// [Indexer] that runs it.
func DefineIndexer(g *Genkit, provider, name string, index func(context.Context, *ai.IndexerRequest) error) ai.Indexer {
	return ai.DefineIndexer(g.reg, provider, name, index)
}

// IsDefinedIndexer reports whether an [Indexer] is defined.
func IsDefinedIndexer(g *Genkit, provider, name string) bool {
	return ai.IsDefinedIndexer(g.reg, provider, name)
}

// LookupIndexer looks up an [Indexer] registered by [DefineIndexer].
// It returns nil if the model was not defined.
func LookupIndexer(g *Genkit, provider, name string) ai.Indexer {
	return ai.LookupIndexer(g.reg, provider, name)
}

// DefineRetriever registers the given retrieve function as an action, and returns a
// [Retriever] that runs it.
func DefineRetriever(g *Genkit, provider, name string, ret func(context.Context, *ai.RetrieverRequest) (*ai.RetrieverResponse, error)) ai.Retriever {
	return ai.DefineRetriever(g.reg, provider, name, ret)
}

// IsDefinedRetriever reports whether a [Retriever] is defined.
func IsDefinedRetriever(g *Genkit, provider, name string) bool {
	return ai.IsDefinedRetriever(g.reg, provider, name)
}

// LookupRetriever looks up a [Retriever] registered by [DefineRetriever].
// It returns nil if the model was not defined.
func LookupRetriever(g *Genkit, provider, name string) ai.Retriever {
	return ai.LookupRetriever(g.reg, provider, name)
}

// DefineEmbedder registers the given embed function as an action, and returns an
// [Embedder] that runs it.
func DefineEmbedder(g *Genkit, provider, name string, embed func(context.Context, *ai.EmbedRequest) (*ai.EmbedResponse, error)) ai.Embedder {
	return ai.DefineEmbedder(g.reg, provider, name, embed)
}

// IsDefinedEmbedder reports whether an embedder is defined.
func IsDefinedEmbedder(g *Genkit, provider, name string) bool {
	return ai.IsDefinedEmbedder(g.reg, provider, name)
}

// LookupEmbedder looks up an [Embedder] registered by [DefineEmbedder].
// It returns nil if the embedder was not defined.
func LookupEmbedder(g *Genkit, provider, name string) ai.Embedder {
	return ai.LookupEmbedder(g.reg, provider, name)
}

// RegisterSpanProcessor registers an OpenTelemetry SpanProcessor for tracing.
func RegisterSpanProcessor(g *Genkit, sp sdktrace.SpanProcessor) {
	g.reg.RegisterSpanProcessor(sp)
}

// optsWithDefaults prepends defaults to the options so that they can be overridden by the caller.
func optsWithDefaults(g *Genkit, opts []ai.GenerateOption) ([]ai.GenerateOption, error) {
	if g.Opts.DefaultModel != "" {
		parts := strings.Split(g.Opts.DefaultModel, "/")
		if len(parts) != 2 {
			return nil, fmt.Errorf("invalid default model format %q, expected provider/name", g.Opts.DefaultModel)
		}
		model := LookupModel(g, parts[0], parts[1])
		if model == nil {
			return nil, fmt.Errorf("default model %q not found", g.Opts.DefaultModel)
		}
		opts = append([]ai.GenerateOption{ai.WithModel(model)}, opts...)
	}
	return opts, nil
}
