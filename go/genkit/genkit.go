// Copyright 2025 Google LLC
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
//
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
	"path/filepath"
	"strings"
	"syscall"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/registry"

	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// Plugin is a common interface for plugins.
type Plugin interface {
	// Name returns the name of the plugin.
	Name() string
	// Init initializes the plugin.
	Init(ctx context.Context, g *Genkit) error
}

// Genkit encapsulates a Genkit instance including the registry, configuration,
// and dev server. It is a required parameter for most Genkit functions.
//
// To create a Genkit instance, use [Init].
type Genkit struct {
	reg          *registry.Registry // Registry for actions, values, and other resources.
	DefaultModel string             // Default model to use if no other model is specified.
	PromptDir    string             // Directory where dotprompts are stored. Will be loaded automatically on initialization.
}

// genkitOptions are options for configuring the Genkit instance.
type genkitOptions struct {
	DefaultModel string   // Default model to use if no other model is specified.
	PromptDir    string   // Directory where dotprompts are stored. Will be loaded automatically on initialization.
	Plugins      []Plugin // Plugin to initialize automatically.
}

type GenkitOption interface {
	apply(g *genkitOptions) error
}

// apply applies the options to the Genkit options.
func (o *genkitOptions) apply(gOpts *genkitOptions) error {
	if o.DefaultModel != "" {
		if gOpts.DefaultModel != "" {
			return errors.New("cannot set default model more than once (WithDefaultModel)")
		}
		gOpts.DefaultModel = o.DefaultModel
	}

	if o.PromptDir != "" {
		if gOpts.PromptDir != "" {
			return errors.New("cannot set prompt directory more than once (WithPromptDir)")
		}
		gOpts.PromptDir = o.PromptDir
	}

	if len(o.Plugins) > 0 {
		if gOpts.Plugins != nil {
			return errors.New("cannot set plugins more than once (WithPlugins)")
		}
		gOpts.Plugins = o.Plugins
	}

	return nil
}

// WithPlugins sets the plugins to use.
func WithPlugins(plugins ...Plugin) GenkitOption {
	return &genkitOptions{Plugins: plugins}
}

// WithDefaultModel sets the default model to use if no model is specified.
func WithDefaultModel(model string) GenkitOption {
	return &genkitOptions{DefaultModel: model}
}

// WithPromptDir sets the directory where dotprompts are stored.
// Defaults to "prompts" at project root. prompts will be automatically
// loaded from this directory on Genkit initialization. Invalid prompt
// files will log errors whereas valid prompt files that result in
// invalid prompt definitions will result in errors.
func WithPromptDir(dir string) GenkitOption {
	return &genkitOptions{PromptDir: dir}
}

// Init creates a new [Genkit] instance.
//
// During local development (`GENKIT_ENV=dev`), it starts the
// Reflection API server (on port 3100 by default) as a side effect.
//
// Example:
//
// This sample assumes you have a prompt file located at `./prompts/jokePrompt.prompt`.
//
//	ctx := context.Background()
//
//	g, err := genkit.Init(ctx,
//		genkit.WithPlugins(googlegenai.GoogleAI{}),
//		genkit.WithDefaultModel("googleai/gemini-2.0-flash"),
//		genkit.WithPromptDir("./prompts"),
//	)
//	if err != nil {
//		log.Fatalf("Failed to initialize Genkit: %v", err)
//	}
//
//	funFact, err := genkit.GenerateText(ctx, g, ai.WithPromptText("Tell me a fake fun fact!"))
//	if err != nil {
//		log.Fatal(err)
//	}
//
//	fmt.Println(funFact) // Might print "Cats have 9 lives!"
//
//	myPrompt, err := genkit.LookupPrompt(g, "", "jokePrompt")
//	if err != nil {
//		log.Fatal(err)
//	}
//
//	resp, err := jokePrompt.Execute(ctx)
//	if err != nil {
//		log.Fatal(err)
//	}
//
//	fmt.Println(resp.Text()) // Might print "Why did the chicken cross the road? To get to the other side!"
func Init(ctx context.Context, opts ...GenkitOption) (*Genkit, error) {
	ctx, _ = signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)

	r, err := registry.New()
	if err != nil {
		return nil, err
	}

	gOpts := &genkitOptions{}
	for _, opt := range opts {
		if err := opt.apply(gOpts); err != nil {
			return nil, fmt.Errorf("genkit.Init: error applying options: %w", err)
		}
	}

	g := &Genkit{
		reg:          r,
		DefaultModel: gOpts.DefaultModel,
		PromptDir:    gOpts.PromptDir,
	}

	for _, plugin := range gOpts.Plugins {
		if err := plugin.Init(ctx, g); err != nil {
			return nil, fmt.Errorf("genkit.Init: plugin %T initialization failed: %w", plugin, err)
		}
	}

	ai.LoadPromptDir(r, gOpts.PromptDir, "")

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
			return nil, fmt.Errorf("genkit.Init: reflection server startup failed: %w", err)
		case <-serverStartCh:
			slog.Debug("reflection server started successfully")
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}

	return g, nil
}

// DefineFlow creates a [core.Flow] that runs fn, and registers it as a [core.Action].
// fn takes an input of type In and returns an output of type Out.
//
// Example:
//
//	myFlow := genkit.DefineFlow(g, "myFlow", func(ctx context.Context, input string) (string, error) {
//		return fmt.Sprintf("You say %q, I say hello!", input), nil
//	})
//
//	myFlow.Run(ctx, "Hello!") // returns 'You say "Hello!", I say "Good morning!"'
func DefineFlow[In, Out any](g *Genkit, name string, fn core.Func[In, Out]) *core.Flow[In, Out, struct{}] {
	return core.DefineFlow(g.reg, name, fn)
}

// DefineStreamingFlow creates a streaming [core.Flow] that runs fn, and registers it as a [core.Action].
//
// fn takes an input of type In and returns an output of type Out, optionally
// streaming values of type Stream incrementally by invoking a callback.
//
// If the function supports streaming and the callback is non-nil, it should
// stream the results by invoking the callback periodically, ultimately returning
// with a final return value that includes all the streamed data.
// Otherwise, it should ignore the callback and just return a result.
//
// Example:
//
//	myFlow := genkit.DefineStreamingFlow(g, "myFlow", func(ctx context.Context, count int, stream func(int) error) (string, error) {
//		for i := 0; i < count; i++ {
//			stream(i)
//		}
//		return fmt.Sprintf("Counted to %d", count), nil
//	})
//
//	// Returns:
//	// Stream value: 0
//	// Stream value: 1
//	// Stream value: 2
//	// Final output: Counted to 3
//	for result, err := range myFlow.Stream(ctx, 3) {
//		if err != nil {
//			log.Printf("Error in stream: %v", err)
//			break
//		}
//		if result.Done {
//			fmt.Println("Final output:", result.Output)
//		} else {
//			fmt.Println("Stream value:", result.Stream)
//		}
//	}
func DefineStreamingFlow[In, Out, Stream any](g *Genkit, name string, fn core.StreamingFunc[In, Out, Stream]) *core.Flow[In, Out, Stream] {
	return core.DefineStreamingFlow(g.reg, name, fn)
}

// Run runs the function fn in the context of the current flow
// and returns what fn returns. It is used to add observability to sub-steps of flows.
//
// Example:
//
//	genkit.DefineFlow(ctx, g, "myFlow", func(ctx context.Context, input string) (string, error) {
//		you, err := genkit.Run(ctx, "yourStep", func() (string, error) {
//			return "You say "+input, nil
//		})
//		if err != nil {
//			return "", err
//		}
//
//		me, err := genkit.Run(ctx, "myStep", func() (string, error) {
//			return "I say, hello!", nil
//		})
//		if err != nil {
//			return "", err
//		}
//
//		return fmt.Sprintf("%s, %s", you, me), nil
//	})
func Run[Out any](ctx context.Context, name string, fn func() (Out, error)) (Out, error) {
	return core.Run(ctx, name, fn)
}

// ListFlows returns all flows registered in the Genkit instance.
// It is used for exposing flows via a server.
//
// Example:
//
//	mux := http.NewServeMux()
//	for _, a := range genkit.ListFlows(g) {
//		mux.HandleFunc("POST /"+a.Name(), genkit.Handler(a))
//	}
//	log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
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

// DefineModel registers the given generate function as an action, and
// returns a [ai.Model] that runs it.
//
// Example:
//
//	model := genkit.DefineModel(g, "myProvider", "myModel", &ModelInfo{
//		Label:       "My Model",
//		Description: "A model to generate amazing text!",
//		Supports: &ModelSupports{
//			Multiturn: true,
//			Tools:     true,
//		},
//	}, func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
//		// Implement the body of your generate function...
//		return &ai.ModelResponse{}, nil
//	})
func DefineModel(g *Genkit, provider, name string, info *ai.ModelInfo, fn ai.ModelFunc) ai.Model {
	return ai.DefineModel(g.reg, provider, name, info, fn)
}

// LookupModel looks up a [ai.Model] registered by [DefineModel].
// It returns nil if the model was not defined.
func LookupModel(g *Genkit, provider, name string) ai.Model {
	return ai.LookupModel(g.reg, provider, name)
}

// DefineTool defines a [ai.Tool] to be passed to a model generate call.
//
// Example:
//
//	jokeTopicTool := genkit.DefineTool(g, "jokeTopic", "Use this to get a topic for a joke", func(ctx *ai.ToolContext, _ any) (string, error) {
//		// Implement the body of your tool...
//		return "chickens", nil
//	})
//
//	joke, err := genkit.GenerateText(ctx, g, ai.WithTools(jokeTopicTool), ai.WithPromptText("Tell me a joke!"))
//	if err != nil {
//		log.Fatal(err)
//	}
//
//	fmt.Println(joke) // Might print "Why did the chicken cross the road? To get to the other side!"
func DefineTool[In, Out any](g *Genkit, name, description string, fn func(ctx *ai.ToolContext, input In) (Out, error)) *ai.ToolDef[In, Out] {
	return ai.DefineTool(g.reg, name, description, fn)
}

// LookupTool looks up the tool in the registry by provided name and returns it.
//
// Example:
//
//	genkit.Generate(ctx, g, ai.WithTools(genkit.LookupTool(g, "jokeTopic")))
func LookupTool(g *Genkit, name string) ai.Tool {
	return ai.LookupTool(g.reg, name)
}

// DefinePrompt defines and registers a prompt with a set of configuration options
// and messages and returns a [ai.Prompt] that can be executed.
//
// This is an alternative to defining and importing a .prompt file, providing
// the most advanced control over how the final request to the model is made.
//
// Prompts can either be rendered into a [ai.GenerateActionOptions] using [Prompt.Render]
// and later passed to [GenerateWithRequest], or executed directly with [Prompt.Execute]
// to generate a [ai.ModelResponse].
//
// Prompts can have some configuration changed at execution time but for the most part
// the configuration is set once when the prompt is defined.
//
// Example:
//
//	type Input struct {
//		Country string `json:"country"`
//	}
//
//	type Output struct {
//		Country string `json:"country"`
//		Capital string `json:"capital"`
//	}
//
//	myPrompt := genkit.DefinePrompt(g, "geographyAssistant",
//		ai.WithModelName("googleai/gemini-2.0-flash"),
//		ai.WithSystemText("You are a helpful assistant teaching a geography lesson."),
//		ai.WithPromptText("What is the capital of {{country}}? If it's not a valid country, answer 'Invalid country'."),
//		ai.WithInputType(Input{Country: "France"}), // Defaults to France if not provided.
//		ai.WithOutputType(Output{}),
//		ai.WithConfig(&GenerationCommonConfig{Temperature: 1}),
//		// ...and many other options!
//	)
//
// Option 1) Render the prompt then call generate with the action options:
//
//	actionOpts, err := myPrompt.Render(ctx)
//	if err != nil {
//		log.Fatal(err)
//	}
//
//	resp, err := genkit.GenerateWithRequest(ctx, g, actionOpts, nil, nil)
//	if err != nil {
//		log.Fatal(err)
//	}
//
//	var out Output
//	if err = resp.UnmarshalOutput(&out); err != nil {
//		log.Fatal(err)
//	}
//
//	fmt.Println(out.Country) // Should print "France"
//	fmt.Println(out.Capital) // Should print "Paris"
//
// Option 2) Execute the prompt directly with the input:
//
//	resp, err := myPrompt.Execute(ctx, ai.WithInput(Input{Country: "Spain"}))
//	if err != nil {
//		log.Fatal(err)
//	}
//
//	var out Output
//	if err = resp.UnmarshalOutput(&out); err != nil {
//		log.Fatal(err)
//	}
//
//	fmt.Println(out.Country) // Should print "Spain"
//	fmt.Println(out.Capital) // Should print "Madrid"
func DefinePrompt(g *Genkit, name string, opts ...ai.PromptOption) (*ai.Prompt, error) {
	return ai.DefinePrompt(g.reg, name, opts...)
}

// LookupPrompt looks up a [Prompt] registered by [DefinePrompt].
// It returns nil if the prompt was not defined.
func LookupPrompt(g *Genkit, provider, name string) *ai.Prompt {
	return ai.LookupPrompt(g.reg, provider, name)
}

// GenerateWithRequest generates a model response using the given options, middleware, and streaming callback. This is to be used in conjunction with DefinePrompt and Prompt.Render().
func GenerateWithRequest(ctx context.Context, g *Genkit, actionOpts *ai.GenerateActionOptions, mw []ai.ModelMiddleware, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
	return ai.GenerateWithRequest(ctx, g.reg, actionOpts, mw, cb)
}

// Generate generates a model response using the given options.
//
// Example:
//
//	resp, err := genkit.Generate(ctx, g, ai.WithPromptText("Tell me a joke!"))
//	if err != nil {
//		log.Fatalf("Failed to generate: %v", err)
//	}
//
//	fmt.Println(resp.Text()) // Might print "Why did the chicken cross the road? To get to the other side!"
func Generate(ctx context.Context, g *Genkit, opts ...ai.GenerateOption) (*ai.ModelResponse, error) {
	return ai.Generate(ctx, g.reg, optsWithDefaults(g, opts)...)
}

// GenerateText generates a model response as text using the given options.
//
// Example:
//
//	text, err := genkit.GenerateText(ctx, g, ai.WithPromptText("Tell me a joke!"))
//	if err != nil {
//		log.Fatalf(err)
//	}
//
//	fmt.Println(text) // Might print "Why did the chicken cross the road? To get to the other side!"
func GenerateText(ctx context.Context, g *Genkit, opts ...ai.GenerateOption) (string, error) {
	return ai.GenerateText(ctx, g.reg, optsWithDefaults(g, opts)...)
}

// GenerateData generates a model response using the given options and fills the value with the structured output.
//
// Example:
//
//	type Joke struct {
//		Topic string `json:"topic"`
//		Text  string `json:"text"`
//	}
//
//	var joke Joke
//	_, err := genkit.GenerateData(ctx, g, &joke, ai.WithPromptText("Tell me a joke!"))
//	if err != nil {
//		log.Fatalf(err)
//	}
//
//	fmt.Println(joke.Topic) // Prints "chickens"
//	fmt.Println(joke.Text) // Might print "Why did the chicken cross the road? To get to the other side!"
func GenerateData(ctx context.Context, g *Genkit, value any, opts ...ai.GenerateOption) (*ai.ModelResponse, error) {
	return ai.GenerateData(ctx, g.reg, value, optsWithDefaults(g, opts)...)
}

// DefineIndexer registers the given index function as an action, and returns an
// [Indexer] that runs it.
func DefineIndexer(g *Genkit, provider, name string, index func(context.Context, *ai.IndexerRequest) error) ai.Indexer {
	return ai.DefineIndexer(g.reg, provider, name, index)
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

// LookupRetriever looks up a [Retriever] registered by [DefineRetriever].
// It returns nil if the retriever was not defined.
func LookupRetriever(g *Genkit, provider, name string) ai.Retriever {
	return ai.LookupRetriever(g.reg, provider, name)
}

// DefineEmbedder registers the given embed function as an action, and returns an
// [Embedder] that runs it.
func DefineEmbedder(g *Genkit, provider, name string, embed func(context.Context, *ai.EmbedRequest) (*ai.EmbedResponse, error)) ai.Embedder {
	return ai.DefineEmbedder(g.reg, provider, name, embed)
}

// LookupEmbedder looks up an [Embedder] registered by [DefineEmbedder].
// It returns nil if the embedder was not defined.
func LookupEmbedder(g *Genkit, provider, name string) ai.Embedder {
	return ai.LookupEmbedder(g.reg, provider, name)
}

// LookupPlugin looks up a plugin registered on initialization.
// It returns nil if the plugin was not registered.
func LookupPlugin(g *Genkit, name string) any {
	return g.reg.LookupPlugin(name)
}

// DefineEvaluator registers the given evaluator function as an action, and
// returns a [Evaluator] that runs it. This method process the input dataset
// one-by-one.
func DefineEvaluator(g *Genkit, provider, name string, options *ai.EvaluatorOptions, eval func(context.Context, *ai.EvaluatorCallbackRequest) (*ai.EvaluatorCallbackResponse, error)) (ai.Evaluator, error) {
	evaluator, err := ai.DefineEvaluator(g.reg, provider, name, options, eval)
	if err != nil {
		return nil, err
	}
	return evaluator, nil
}

// DefineBatchEvaluator registers the given evaluator function as an action, and
// returns a [Evaluator] that runs it. This method provide the full
// [EvaluatorRequest] to the callback function, giving more flexibilty to the
// user for processing the data, such as batching or parallelization.
func DefineBatchEvaluator(g *Genkit, provider, name string, options *ai.EvaluatorOptions, eval func(context.Context, *ai.EvaluatorRequest) (*ai.EvaluatorResponse, error)) (ai.Evaluator, error) {
	evaluator, err := ai.DefineBatchEvaluator(g.reg, provider, name, options, eval)
	if err != nil {
		return nil, err
	}
	return evaluator, nil
}

// LookupEvaluator looks up a [Evaluator] registered by [DefineEvaluator].
// It returns nil if the evaluator was not defined.
func LookupEvaluator(g *Genkit, provider, name string) ai.Evaluator {
	return ai.LookupEvaluator(g.reg, provider, name)
}

// LoadPromptDir loads all prompts and partials from a given directory with the specified namespace.
func LoadPromptDir(g *Genkit, dir string, namespace string) error {
	return ai.LoadPromptDir(g.reg, dir, namespace)
}

// LoadPrompt loads a prompt from a given filepath with the specified namespace.
func LoadPrompt(g *Genkit, path string, namespace string) (*ai.Prompt, error) {
	dir, filename := filepath.Split(path)
	if dir != "" {
		dir = filepath.Clean(dir)
	}

	return ai.LoadPrompt(g.reg, dir, filename, namespace)
}

// RegisterSpanProcessor registers an OpenTelemetry SpanProcessor for tracing.
func RegisterSpanProcessor(g *Genkit, sp sdktrace.SpanProcessor) {
	g.reg.RegisterSpanProcessor(sp)
}

// optsWithDefaults prepends defaults to the options so that they can be overridden by the caller.
func optsWithDefaults(g *Genkit, opts []ai.GenerateOption) []ai.GenerateOption {
	if g.DefaultModel != "" {
		opts = append([]ai.GenerateOption{ai.WithModelName(g.DefaultModel)}, opts...)
	}
	return opts
}
