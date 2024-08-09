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

package genkit

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/metrics"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/google/uuid"
	"github.com/invopop/jsonschema"
	otrace "go.opentelemetry.io/otel/trace"
)

// TODO: support auth
// TODO: provide a way to start a Flow from user code.

// A Flow is a kind of Action that can be interrupted and resumed.
// (Resumption is an experimental feature in the Javascript implementation,
// and not yet supported in Go.)
//
// A Flow[In, Out, Stream] represents a function from I to O (the S parameter is for streaming,
// described below). But the function may run in pieces, with interruptions and resumptions.
// (The interruptions discussed here are a part of the flow mechanism, not hardware
// interrupts.) The actual Go function for the flow may be executed multiple times,
// each time making more progress, until finally it completes with a value of type
// O or an error. The mechanism used to achieve this is explained below.
//
// To treat a flow as an action, which is an uninterrupted function execution, we
// use different input and output types to capture the additional behavior. The input
// to a flow action is an instruction about what to do: start running on the input,
// resume after being suspended, and others. This is the type flowInstruction[I]
// (called FlowInvokeEnvelopeMessage in the javascript code).
//
// The output of a flow action may contain the final output of type O if the flow
// finishes, but in general contains the state of the flow, including an ID to retrieve
// it later, what caused it to block, and so on.
//
// A flow consists of ordinary code, and can be interrupted on one machine and resumed
// on another, even if the underlying system has no support for process migration.
// To accomplish this, flowStates include the original input, and resuming a flow
// involves loading its flowState from storage and re-running its Go function from
// the beginning. To avoid repeating expensive work, parts of the flow, called steps,
// are cached in the flowState. The programmer marks these steps manually, by calling
// genkit.Run.
//
// A flow computation consists of one or more flow executions. (The flowExecution
// type records information about these; a flowState holds a slice of flowExecutions.)
// The computation begins with a "start" instruction. If the function is not interrupted,
// it will run to completion and the final state will contain its result. If it is
// interrupted, state will contain information about how and when it can be resumed.
// A "resume" instruction will run the Go function again using the information in
// the saved state.
//
// Another way to start a flow is to schedule it for some time in the future. The
// "schedule" instruction accomplishes this; the flow is finally started at a later
// time by the "runScheduled" instruction.
//
// Some flows can "stream" their results, providing them incrementally. To do so,
// the flow invokes a callback repeatedly. When streaming is complete, the flow
// returns a final result in the usual way.
//
// Streaming is only supported for the "start" flow instruction. Currently there is
// no way to schedule or resume a flow with streaming.

// A Flow is an Action with additional support for observability and introspection.
// A Flow[In, Out, Stream] represents a function from In to Out. The Stream parameter is for
// flows that support streaming: providing their results incrementally.
type Flow[In, Out, Stream any] struct {
	name         string                     // The last component of the flow's key in the registry.
	fn           core.Func[In, Out, Stream] // The function to run.
	stateStore   core.FlowStateStore        // Where FlowStates are stored, to support resumption.
	tstate       *tracing.State             // set from the action when the flow is defined
	inputSchema  *jsonschema.Schema         // Schema of the input to the flow
	outputSchema *jsonschema.Schema         // Schema of the output out of the flow
	auth         FlowAuth                   // Auth provider and policy checker for the flow.
	// TODO: scheduler
	// TODO: experimentalDurable
	// TODO: middleware
}

// runOptions configures a single flow run.
type runOptions struct {
	authContext AuthContext // Auth context to pass to auth policy checker when calling a flow directly.
}

// flowOptions configures a flow.
type flowOptions struct {
	auth FlowAuth // Auth provider and policy checker for the flow.
}

type noStream = func(context.Context, struct{}) error

// AuthContext is the type of the auth context passed to the auth policy checker.
type AuthContext map[string]any

// FlowAuth configures an auth context provider and an auth policy check for a flow.
type FlowAuth interface {
	// ProvideAuthContext sets the auth context on the given context by parsing an auth header.
	// The parsing logic is provided by the auth provider.
	ProvideAuthContext(ctx context.Context, authHeader string) (context.Context, error)

	// NewContext sets the auth context on the given context. This is used when
	// the auth context is provided by the user, rather than by the auth provider.
	NewContext(ctx context.Context, authContext AuthContext) context.Context

	// FromContext retrieves the auth context from the given context.
	FromContext(ctx context.Context) AuthContext

	// CheckAuthPolicy checks the auth context against policy.
	CheckAuthPolicy(ctx context.Context, input any) error
}

// streamingCallback is the type of streaming callbacks.
type streamingCallback[Stream any] func(context.Context, Stream) error

// FlowOption modifies the flow with the provided option.
type FlowOption func(opts *flowOptions)

// FlowRunOption modifies a flow run with the provided option.
type FlowRunOption func(opts *runOptions)

// WithFlowAuth sets an auth provider and policy checker for the flow.
func WithFlowAuth(auth FlowAuth) FlowOption {
	return func(f *flowOptions) {
		if f.auth != nil {
			log.Panic("auth already set in flow")
		}
		f.auth = auth
	}
}

// WithLocalAuth configures an option to run or stream a flow with a local auth value.
func WithLocalAuth(authContext AuthContext) FlowRunOption {
	return func(opts *runOptions) {
		if opts.authContext != nil {
			log.Panic("authContext already set in runOptions")
		}
		opts.authContext = authContext
	}
}

// DefineFlow creates a Flow that runs fn, and registers it as an action.
//
// fn takes an input of type In and returns an output of type Out.
func DefineFlow[In, Out any](
	name string,
	fn func(ctx context.Context, input In) (Out, error),
	opts ...FlowOption,
) *Flow[In, Out, struct{}] {
	return defineFlow(registry.Global, name, core.Func[In, Out, struct{}](
		func(ctx context.Context, input In, cb func(ctx context.Context, _ struct{}) error) (Out, error) {
			return fn(ctx, input)
		}), opts...)
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
	name string,
	fn func(ctx context.Context, input In, callback func(context.Context, Stream) error) (Out, error),
	opts ...FlowOption,
) *Flow[In, Out, Stream] {
	return defineFlow(registry.Global, name, core.Func[In, Out, Stream](fn), opts...)
}

func defineFlow[In, Out, Stream any](r *registry.Registry, name string, fn core.Func[In, Out, Stream], opts ...FlowOption) *Flow[In, Out, Stream] {
	var i In
	var o Out
	f := &Flow[In, Out, Stream]{
		name:         name,
		fn:           fn,
		inputSchema:  base.InferJSONSchema(i),
		outputSchema: base.InferJSONSchema(o),
		// TODO: set stateStore?
	}
	flowOpts := &flowOptions{}
	for _, opt := range opts {
		opt(flowOpts)
	}
	f.auth = flowOpts.auth
	metadata := map[string]any{
		"inputSchema":  f.inputSchema,
		"outputSchema": f.outputSchema,
		"requiresAuth": f.auth != nil,
	}
	afunc := func(ctx context.Context, inst *flowInstruction[In], cb func(context.Context, Stream) error) (*flowState[In, Out], error) {
		tracing.SetCustomMetadataAttr(ctx, "flow:wrapperAction", "true")
		// Only non-durable flows have an auth policy so can safely assume Start.Input.
		if inst.Start != nil {
			if f.auth != nil {
				ctx = f.auth.NewContext(ctx, inst.Auth)
			}
			if err := f.checkAuthPolicy(ctx, any(inst.Start.Input)); err != nil {
				return nil, err
			}
		}
		return f.runInstruction(ctx, inst, streamingCallback[Stream](cb))
	}
	core.DefineActionInRegistry(r, "", f.name, atype.Flow, metadata, nil, afunc)
	f.tstate = r.TracingState()
	r.RegisterFlow(f)
	return f
}

// TODO: use flowError?

// A flowInstruction is an instruction to follow with a flow.
// It is the input for the flow's action.
// Exactly one field will be non-nil.
type flowInstruction[In any] struct {
	Start        *startInstruction[In]    `json:"start,omitempty"`
	Resume       *resumeInstruction       `json:"resume,omitempty"`
	Schedule     *scheduleInstruction[In] `json:"schedule,omitempty"`
	RunScheduled *runScheduledInstruction `json:"runScheduled,omitempty"`
	State        *stateInstruction        `json:"state,omitempty"`
	Retry        *retryInstruction        `json:"retry,omitempty"`
	Auth         map[string]any           `json:"auth,omitempty"`
}

// A startInstruction starts a flow.
type startInstruction[In any] struct {
	Input  In                `json:"input,omitempty"`
	Labels map[string]string `json:"labels,omitempty"`
}

// A resumeInstruction resumes a flow that was started and then interrupted.
type resumeInstruction struct {
	FlowID  string `json:"flowId,omitempty"`
	Payload any    `json:"payload,omitempty"`
}

// A scheduleInstruction schedules a flow to start at a later time.
type scheduleInstruction[In any] struct {
	DelaySecs float64 `json:"delay,omitempty"`
	Input     In      `json:"input,omitempty"`
}

// A runScheduledInstruction starts a scheduled flow.
type runScheduledInstruction struct {
	FlowID string `json:"flowId,omitempty"`
}

// A stateInstruction retrieves the flowState from the flow.
type stateInstruction struct {
	FlowID string `json:"flowId,omitempty"`
}

// TODO: document
type retryInstruction struct {
	FlowID string `json:"flowId,omitempty"`
}

// A flowState is a persistent representation of a flow that may be in the middle of running.
// It contains all the information needed to resume a flow, including the original input
// and a cache of all completed steps.
type flowState[In, Out any] struct {
	FlowID   string `json:"flowId,omitempty"`
	FlowName string `json:"name,omitempty"`
	// start time in milliseconds since the epoch
	StartTime       tracing.Milliseconds `json:"startTime,omitempty"`
	Input           In                   `json:"input,omitempty"`
	mu              sync.Mutex
	Cache           map[string]json.RawMessage `json:"cache,omitempty"`
	EventsTriggered map[string]any             `json:"eventsTriggered,omitempty"`
	Executions      []*flowExecution           `json:"executions,omitempty"`
	// The operation is the user-visible part of the state.
	Operation    *operation[Out] `json:"operation,omitempty"`
	TraceContext string          `json:"traceContext,omitempty"`
}

func newFlowState[In, Out any](id, name string, input In) *flowState[In, Out] {
	return &flowState[In, Out]{
		FlowID:    id,
		FlowName:  name,
		Input:     input,
		StartTime: tracing.ToMilliseconds(time.Now()),
		Cache:     map[string]json.RawMessage{},
		Operation: &operation[Out]{
			FlowID: id,
			Done:   false,
		},
	}
}

// flowState implements base.FlowStater.
func (fs *flowState[In, Out]) IsFlowState() {}

func (fs *flowState[In, Out]) ToJSON() ([]byte, error) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetIndent("", "    ") // make the value easy to read for debugging
	if err := enc.Encode(fs); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

func (fs *flowState[In, Out]) CacheAt(key string) json.RawMessage {
	fs.mu.Lock()
	defer fs.mu.Unlock()
	return fs.Cache[key]
}

func (fs *flowState[In, Out]) CacheSet(key string, val json.RawMessage) {
	fs.mu.Lock()
	defer fs.mu.Unlock()
	fs.Cache[key] = val
}

// An operation describes the state of a Flow that may still be in progress.
type operation[Out any] struct {
	FlowID string `json:"name,omitempty"`
	// The step that the flow is blocked on, if any.
	BlockedOnStep *struct {
		Name   string `json:"name"`
		Schema string `json:"schema"`
	} `json:"blockedOnStep,omitempty"`
	// Whether the operation is completed.
	// If true Result will be non-nil.
	Done bool `json:"done,omitempty"`
	// Service-specific metadata associated with the operation. It typically contains progress information and common metadata such as create time.
	Metadata any              `json:"metadata,omitempty"`
	Result   *FlowResult[Out] `json:"result,omitempty"`
}

// A FlowResult is the result of a flow: either success, in which case Response is
// the return value of the flow's function; or failure, in which case Error is the
// non-empty error string.
type FlowResult[Out any] struct {
	Response Out    `json:"response,omitempty"`
	Error    string `json:"error,omitempty"`
	// The Error field above is not used in the code, but it gets marshaled
	// into JSON.
	// TODO: replace with  a type that implements error and json.Marshaler.
	err        error
	StackTrace string `json:"stacktrace,omitempty"`
}

// FlowResult is called FlowResponse in the javascript.

// runInstruction performs one of several actions on a flow, as determined by msg.
// (Called runEnvelope in the js.)
func (f *Flow[In, Out, Stream]) runInstruction(ctx context.Context, inst *flowInstruction[In], cb streamingCallback[Stream]) (*flowState[In, Out], error) {
	switch {
	case inst.Start != nil:
		// TODO: pass msg.Start.Labels.
		return f.start(ctx, inst.Start.Input, cb)
	case inst.Resume != nil:
		return nil, errors.ErrUnsupported
	case inst.Retry != nil:
		return nil, errors.ErrUnsupported
	case inst.RunScheduled != nil:
		return nil, errors.ErrUnsupported
	case inst.Schedule != nil:
		return nil, errors.ErrUnsupported
	case inst.State != nil:
		return nil, errors.ErrUnsupported
	default:
		return nil, errors.New("all known fields of FlowInvokeEnvelopeMessage are nil")
	}
}

// The following methods make Flow[I, O, S] implement the flow interface, define in servers.go.

// Name returns the name that the flow was defined with.
func (f *Flow[In, Out, Stream]) Name() string { return f.name }

func (f *Flow[In, Out, Stream]) runJSON(ctx context.Context, authHeader string, input json.RawMessage, cb streamingCallback[json.RawMessage]) (json.RawMessage, error) {
	// Validate input before unmarshaling it because invalid or unknown fields will be discarded in the process.
	if err := base.ValidateJSON(input, f.inputSchema); err != nil {
		return nil, &base.HTTPError{Code: http.StatusBadRequest, Err: err}
	}
	var in In
	if err := json.Unmarshal(input, &in); err != nil {
		return nil, &base.HTTPError{Code: http.StatusBadRequest, Err: err}
	}
	newCtx, err := f.provideAuthContext(ctx, authHeader)
	if err != nil {
		return nil, &base.HTTPError{Code: http.StatusUnauthorized, Err: err}
	}
	if err := f.checkAuthPolicy(newCtx, in); err != nil {
		return nil, &base.HTTPError{Code: http.StatusForbidden, Err: err}
	}
	// If there is a callback, wrap it to turn an S into a json.RawMessage.
	var callback streamingCallback[Stream]
	if cb != nil {
		callback = func(ctx context.Context, s Stream) error {
			bytes, err := json.Marshal(s)
			if err != nil {
				return err
			}
			return cb(ctx, json.RawMessage(bytes))
		}
	}
	fstate, err := f.start(ctx, in, callback)
	if err != nil {
		return nil, err
	}
	if fstate.Operation == nil {
		return nil, errors.New("nil operation")
	}
	res := fstate.Operation.Result
	if res == nil {
		return nil, errors.New("nil result")
	}
	if res.err != nil {
		return nil, res.err
	}
	return json.Marshal(res.Response)
}

// provideAuthContext provides auth context for the given auth header if flow auth is configured.
func (f *Flow[In, Out, Stream]) provideAuthContext(ctx context.Context, authHeader string) (context.Context, error) {
	if f.auth != nil {
		newCtx, err := f.auth.ProvideAuthContext(ctx, authHeader)
		if err != nil {
			return nil, fmt.Errorf("unauthorized: %w", err)
		}
		return newCtx, nil
	}
	return ctx, nil
}

// checkAuthPolicy checks auth context against the policy if flow auth is configured.
func (f *Flow[In, Out, Stream]) checkAuthPolicy(ctx context.Context, input any) error {
	if f.auth != nil {
		if err := f.auth.CheckAuthPolicy(ctx, input); err != nil {
			return fmt.Errorf("permission denied for resource: %w", err)
		}
	}
	return nil
}

// start starts executing the flow with the given input.
func (f *Flow[In, Out, Stream]) start(ctx context.Context, input In, cb streamingCallback[Stream]) (_ *flowState[In, Out], err error) {
	flowID, err := generateFlowID()
	if err != nil {
		return nil, err
	}
	state := newFlowState[In, Out](flowID, f.name, input)
	f.execute(ctx, state, "start", cb)
	return state, nil
}

// execute performs one flow execution.
// Using its flowState argument as a starting point, it runs the flow function until
// it finishes or is interrupted.
// It updates the passed flowState to reflect the new state of the flow compuation.
//
// This function corresponds to Flow.executeSteps in the js, but does more:
// it creates the flowContext and saves the state.
func (f *Flow[In, Out, Stream]) execute(ctx context.Context, state *flowState[In, Out], dispatchType string, cb streamingCallback[Stream]) {
	fctx := newFlowContext(state, f.stateStore, f.tstate)
	defer func() {
		if err := fctx.finish(ctx); err != nil {
			// TODO: do something more with this error?
			logger.FromContext(ctx).Error("flowContext.finish", "err", err.Error())
		}
	}()
	ctx = flowContextKey.NewContext(ctx, fctx)
	exec := &flowExecution{
		StartTime: tracing.ToMilliseconds(time.Now()),
	}
	state.mu.Lock()
	state.Executions = append(state.Executions, exec)
	state.mu.Unlock()
	// TODO: retrieve the JSON-marshaled SpanContext from state.traceContext.
	// TODO: add a span link to the context.
	output, err := tracing.RunInNewSpan(ctx, fctx.tracingState(), f.name, "flow", true, state.Input, func(ctx context.Context, input In) (Out, error) {
		tracing.SetCustomMetadataAttr(ctx, "flow:execution", strconv.Itoa(len(state.Executions)-1))
		// TODO: put labels into span metadata.
		tracing.SetCustomMetadataAttr(ctx, "flow:name", f.name)
		tracing.SetCustomMetadataAttr(ctx, "flow:id", state.FlowID)
		tracing.SetCustomMetadataAttr(ctx, "flow:dispatchType", dispatchType)
		rootSpanContext := otrace.SpanContextFromContext(ctx)
		traceID := rootSpanContext.TraceID().String()
		exec.TraceIDs = append(exec.TraceIDs, traceID)
		// TODO: Save rootSpanContext in the state.
		// TODO: If input is missing, get it from state.input and overwrite metadata.input.
		start := time.Now()
		var err error
		if err = base.ValidateValue(input, f.inputSchema); err != nil {
			err = fmt.Errorf("invalid input: %w", err)
		}
		var output Out
		if err == nil {
			output, err = f.fn(ctx, input, cb)
			if err == nil {
				if err = base.ValidateValue(output, f.outputSchema); err != nil {
					err = fmt.Errorf("invalid output: %w", err)
				}
			}
		}
		latency := time.Since(start)
		if err != nil {
			// TODO: handle InterruptError
			logger.FromContext(ctx).Error("flow failed",
				"path", tracing.SpanPath(ctx),
				"err", err.Error(),
			)
			metrics.WriteFlowFailure(ctx, f.name, latency, err)
			tracing.SetCustomMetadataAttr(ctx, "flow:state", "error")
		} else {
			logger.FromContext(ctx).Info("flow succeeded", "path", tracing.SpanPath(ctx))
			metrics.WriteFlowSuccess(ctx, f.name, latency)
			tracing.SetCustomMetadataAttr(ctx, "flow:state", "done")

		}
		// TODO: telemetry
		return output, err
	})
	// TODO: perhaps this should be in a defer, to handle panics?
	state.mu.Lock()
	defer state.mu.Unlock()
	state.Operation.Done = true
	if err != nil {
		state.Operation.Result = &FlowResult[Out]{
			err:   err,
			Error: err.Error(),
			// TODO: stack trace?
		}
	} else {
		state.Operation.Result = &FlowResult[Out]{Response: output}
	}
}

// generateFlowID returns a unique ID for identifying a flow execution.
func generateFlowID() (string, error) {
	// v4 UUID, as in the js code.
	id, err := uuid.NewRandom()
	if err != nil {
		return "", err
	}
	return id.String(), nil
}

// A flowContext holds dynamically accessible information about a flow.
// A flowContext is created when a flow starts running, and is stored
// in a context.Context so it can be accessed from within the currrently active flow.
type flowContext[I, O any] struct {
	state      *flowState[I, O]
	stateStore core.FlowStateStore
	tstate     *tracing.State
	mu         sync.Mutex
	seenSteps  map[string]int // number of times each name appears, to avoid duplicate names
	// TODO: auth
}

// flowContexter is the type of all flowContext[I, O].
type flowContexter interface {
	uniqueStepName(string) string
	stater() base.FlowStater
	tracingState() *tracing.State
}

func newFlowContext[I, O any](state *flowState[I, O], store core.FlowStateStore, tstate *tracing.State) *flowContext[I, O] {
	return &flowContext[I, O]{
		state:      state,
		stateStore: store,
		tstate:     tstate,
		seenSteps:  map[string]int{},
	}
}
func (fc *flowContext[I, O]) stater() base.FlowStater      { return fc.state }
func (fc *flowContext[I, O]) tracingState() *tracing.State { return fc.tstate }

// finish is called at the end of a flow execution.
func (fc *flowContext[I, O]) finish(ctx context.Context) error {
	if fc.stateStore == nil {
		return nil
	}
	// TODO: In the js, start saves the state only under certain conditions. Duplicate?
	return fc.stateStore.Save(ctx, fc.state.FlowID, fc.state)
}

// uniqueStepName returns a name that is unique for this flow execution.
func (fc *flowContext[I, O]) uniqueStepName(name string) string {
	fc.mu.Lock()
	defer fc.mu.Unlock()
	n := fc.seenSteps[name]
	fc.seenSteps[name] = n + 1
	if n == 0 {
		return name
	}
	return fmt.Sprintf("%s-%d", name, n)
}

var flowContextKey = base.NewContextKey[flowContexter]()

// Run runs the function f in the context of the current flow
// and returns what f returns.
// It returns an error if no flow is active.
//
// Each call to Run results in a new step in the flow.
// A step has its own span in the trace, and its result is cached so that if the flow
// is restarted, f will not be called a second time.
func Run[Out any](ctx context.Context, name string, f func() (Out, error)) (Out, error) {
	// from js/flow/src/steps.ts
	fc := flowContextKey.FromContext(ctx)
	if fc == nil {
		var z Out
		return z, fmt.Errorf("genkit.Run(%q): must be called from a flow", name)
	}
	// TODO: The input here is irrelevant. Perhaps runInNewSpan should have only a result type param,
	// as in the js.
	return tracing.RunInNewSpan(ctx, fc.tracingState(), name, "flowStep", false, 0, func(ctx context.Context, _ int) (Out, error) {
		uName := fc.uniqueStepName(name)
		tracing.SetCustomMetadataAttr(ctx, "flow:stepType", "run")
		tracing.SetCustomMetadataAttr(ctx, "flow:stepName", name)
		tracing.SetCustomMetadataAttr(ctx, "flow:resolvedStepName", uName)
		// Memoize the function call, using the cache in the flowState.
		// The locking here prevents corruption of the cache from concurrent access, but doesn't
		// prevent two goroutines racing to check the cache and call f. However, that shouldn't
		// happen because every step has a unique cache key.
		// TODO: don't memoize a nested flow (see context.ts)
		fs := fc.stater()
		j := fs.CacheAt(uName)
		if j != nil {
			var t Out
			if err := json.Unmarshal(j, &t); err != nil {
				return base.Zero[Out](), err
			}
			tracing.SetCustomMetadataAttr(ctx, "flow:state", "cached")
			return t, nil
		}
		t, err := f()
		if err != nil {
			return base.Zero[Out](), err
		}
		bytes, err := json.Marshal(t)
		if err != nil {
			return base.Zero[Out](), err
		}
		fs.CacheSet(uName, json.RawMessage(bytes))
		tracing.SetCustomMetadataAttr(ctx, "flow:state", "run")
		return t, nil
	})
}

// Run runs the flow in the context of another flow. The flow must run to completion when started
// (that is, it must not have interrupts).
func (f *Flow[In, Out, Stream]) Run(ctx context.Context, input In, opts ...FlowRunOption) (Out, error) {
	return f.run(ctx, input, nil, opts...)
}

func (f *Flow[In, Out, Stream]) run(ctx context.Context, input In, cb func(context.Context, Stream) error, opts ...FlowRunOption) (Out, error) {
	runOpts := &runOptions{}
	for _, opt := range opts {
		opt(runOpts)
	}
	if runOpts.authContext != nil && f.auth != nil {
		ctx = f.auth.NewContext(ctx, runOpts.authContext)
	}
	if err := f.checkAuthPolicy(ctx, input); err != nil {
		return base.Zero[Out](), err
	}
	state, err := f.start(ctx, input, cb)
	if err != nil {
		return base.Zero[Out](), err
	}
	return finishedOpResponse(state.Operation)
}

// FlowIterator defines the interface for iterating over flow results.
type FlowIterator[Out, Stream any] interface {
	Next() (Stream, bool)
	FinalOutput() (Out, error)
}

// flowIterator implements the FlowIterator interface.
type flowIterator[Out, Stream any] struct {
	done     bool
	output   Out
	err      error
	streamCh chan Stream
	doneCh   chan struct{}
}

// Next returns the next streamed value or an error if the flow has completed or failed.
func (fi *flowIterator[Out, Stream]) Next() (*Stream, bool) {
	select {
	case stream := <-fi.streamCh:
		return &stream, false
	case <-fi.doneCh:
		return nil, true
	}
}

// FinalOutput returns the final output of the flow if it has completed.
func (fi *flowIterator[Out, Stream]) FinalOutput() (*Out, error) {
	if !fi.done {
		return nil, errors.New("flow has not completed")
	}
	if fi.err != nil {
		return nil, fi.err
	}
	return &fi.output, nil
}

// Stream returns a FlowIterator for the flow.
func (f *Flow[In, Out, Stream]) Stream(ctx context.Context, input In, opts ...FlowRunOption) FlowIterator[*Out, *Stream] {
	fi := &flowIterator[Out, Stream]{
		done:     false,
		streamCh: make(chan Stream),
		doneCh:   make(chan struct{}),
	}

	go func() {
		cb := func(ctx context.Context, s Stream) error {
			if ctx.Err() != nil {
				fi.err = ctx.Err()
				return ctx.Err()
			}
			select {
			case fi.streamCh <- s:
				return nil
			case <-ctx.Done():
				return ctx.Err()
			}
		}
		output, err := f.run(ctx, input, cb, opts...)
		if err != nil {
			fi.err = err
		} else {
			fi.output = output
		}
		fi.done = true
		close(fi.doneCh)
	}()

	return fi
}

var errStop = errors.New("stop")

func finishedOpResponse[O any](op *operation[O]) (O, error) {
	if !op.Done {
		return base.Zero[O](), fmt.Errorf("flow %s did not finish execution", op.FlowID)
	}
	if op.Result.err != nil {
		return base.Zero[O](), fmt.Errorf("flow %s: %w", op.FlowID, op.Result.err)
	}
	return op.Result.Response, nil
}
