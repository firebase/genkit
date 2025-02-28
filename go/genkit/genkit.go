// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Package genkit provides Genkit functionality for application developers.
package genkit

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/invopop/jsonschema"

	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// Genkit encapsulates a Genkit instance including the registry and configuration.
type Genkit struct {
	// Registry for all actions contained in this instance.
	reg *registry.Registry
	// Params to configure calls using this instance.
	Params *GenkitParams
}

type genkitOption = func(params *GenkitParams) error

type GenkitParams struct {
	DefaultModel string // The default model to use if no model is specified.
	PromptDir    string // Directory where dotprompts are stored.
}

// WithDefaultModel sets the default model to use if no model is specified.
func WithDefaultModel(model string) genkitOption {
	return func(params *GenkitParams) error {
		if params.DefaultModel != "" {
			return errors.New("genkit.WithDefaultModel: cannot set DefaultModel more than once")
		}
		params.DefaultModel = model
		return nil
	}
}

// WithPromptDir sets the directory where dotprompts are stored. Defaults to "prompts" at project root.
func WithPromptDir(dir string) genkitOption {
	return func(params *GenkitParams) error {
		if params.PromptDir != "" {
			return errors.New("genkit.WithPromptDir: cannot set PromptDir more than once")
		}
		params.PromptDir = dir
		return nil
	}
}

// Init creates a new Genkit instance.
//
// During local development (GENKIT_ENV=dev), it starts the Reflection API server (default :3100) as a side effect.
func Init(ctx context.Context, opts ...genkitOption) (*Genkit, error) {
	ctx, _ = signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)

	r, err := registry.New()
	if err != nil {
		return nil, err
	}

	params := &GenkitParams{}
	for _, opt := range opts {
		if err := opt(params); err != nil {
			return nil, err
		}
	}

	if params.DefaultModel != "" {
		_, err := modelRefParts(params.DefaultModel)
		if err != nil {
			return nil, err
		}
	}

	if registry.CurrentEnvironment() == registry.EnvironmentDev {
		errCh := make(chan error, 1)
		serverStartCh := make(chan struct{})

		go func() {
			if s := startReflectionServer(ctx, r, errCh, serverStartCh); s == nil {
				return
			}
			if err := <-errCh; err != nil {
				slog.Error("reflection server error", "err", err)
			}
		}()

		select {
		case err := <-errCh:
			return nil, fmt.Errorf("reflection server startup failed: %w", err)
		case <-serverStartCh:
			slog.Debug("reflection server started successfully")
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}

	return &Genkit{
		reg:    r,
		Params: params,
	}, nil
}

// DefineFlow creates a Flow that runs fn, and registers it as an action. fn takes an input of type In and returns an output of type Out.
func DefineFlow[In, Out any](
	g *Genkit,
	name string,
	fn core.Func[In, Out],
) *core.Flow[In, Out, struct{}] {
	return core.DefineFlow(g.reg, name, fn)
}

// DefineStreamingFlow creates a streaming Flow that runs fn, and registers it as an action.
//
// fn takes an input of type In and returns an output of type Out, optionally
// streaming values of type Stream incrementally by invoking a callback.
//
// If the function supports streaming and the callback is non-nil, it should
// stream the results by invoking the callback periodically, ultimately returning
// with a final return value that includes all the streamed data.
// Otherwise, it should ignore the callback and just return a result.
func DefineStreamingFlow[In, Out, Stream any](
	g *Genkit,
	name string,
	fn core.StreamingFunc[In, Out, Stream],
) *core.Flow[In, Out, Stream] {
	return core.DefineStreamingFlow(g.reg, name, fn)
}

// Run runs the function f in the context of the current flow
// and returns what f returns.
// It returns an error if no flow is active.
//
// Each call to Run results in a new step in the flow.
// A step has its own span in the trace, and its result is cached so that if the flow
// is restarted, f will not be called a second time.
func Run[Out any](ctx context.Context, name string, f func() (Out, error)) (Out, error) {
	return core.Run(ctx, name, f)
}

// ListFlows returns all flows registered in the Genkit instance.
func ListFlows(g *Genkit) []core.Action {
	acts := g.reg.ListActions()
	flows := []core.Action{}
	for _, act := range acts {
		if strings.HasPrefix(act.Key, "/"+string(atype.Flow)+"/") {
			flows = append(flows, g.reg.LookupAction(act.Key))
		}
	}
	return flows
}

// DefineModel registers the given generate function as an action, and returns a [Model] that runs it.
func DefineModel(
	g *Genkit,
	provider, name string,
	info *ai.ModelInfo,
	generate ai.ModelFunc,
) ai.Model {
	return ai.DefineModel(g.reg, provider, name, info, generate)
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
func DefineTool[In, Out any](g *Genkit, name, description string, fn func(ctx *ai.ToolContext, input In) (Out, error)) *ai.ToolDef[In, Out] {
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
func GenerateWithRequest(ctx context.Context, g *Genkit, m ai.Model, req *ai.ModelRequest, mw []ai.ModelMiddleware, toolCfg *ai.ToolConfig, cb ai.ModelStreamingCallback) (*ai.ModelResponse, error) {
	return m.Generate(ctx, g.reg, req, mw, toolCfg, cb)
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
	if g.Params.DefaultModel != "" {
		parts, err := modelRefParts(g.Params.DefaultModel)
		if err != nil {
			return nil, err
		}
		model := LookupModel(g, parts[0], parts[1])
		if model == nil {
			return nil, fmt.Errorf("default model %q not found", g.Params.DefaultModel)
		}
		opts = append([]ai.GenerateOption{ai.WithModel(model)}, opts...)
	}
	return opts, nil
}

// modelRefParts parses a model string into a provider and name.
func modelRefParts(model string) ([]string, error) {
	parts := strings.Split(model, "/")
	if len(parts) != 2 {
		return nil, fmt.Errorf("invalid model format %q, expected provider/name", model)
	}
	return parts, nil
}
