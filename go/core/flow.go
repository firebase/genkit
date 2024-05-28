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

package core

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal"
	"github.com/google/uuid"
	otrace "go.opentelemetry.io/otel/trace"
)

// TODO(jba): support auth
// TODO(jba): provide a way to start a Flow from user code.

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
// A flow that doesn't support streaming can use [NoStream] as its third type parameter.
//
// Streaming is only supported for the "start" flow instruction. Currently there is
// no way to schedule or resume a flow with streaming.

// A Flow is an Action with additional support for observability and introspection.
// A Flow[In, Out, Stream] represents a function from In to Out. The Stream parameter is for
// flows that support streaming: providing their results incrementally.
type Flow[In, Out, Stream any] struct {
	name       string                // The last component of the flow's key in the registry.
	fn         Func[In, Out, Stream] // The function to run.
	stateStore FlowStateStore        // Where FlowStates are stored, to support resumption.
	tstate     *tracing.State        // set from the action when the flow is defined
	// TODO(jba): scheduler
	// TODO(jba): experimentalDurable
	// TODO(jba): authPolicy
	// TODO(jba): middleware
}

// DefineFlow creates a Flow that runs fn, and registers it as an action.
func DefineFlow[In, Out, Stream any](name string, fn Func[In, Out, Stream]) *Flow[In, Out, Stream] {
	return defineFlow(globalRegistry, name, fn)
}

func defineFlow[In, Out, Stream any](r *registry, name string, fn Func[In, Out, Stream]) *Flow[In, Out, Stream] {
	f := &Flow[In, Out, Stream]{
		name: name,
		fn:   fn,
		// TODO(jba): set stateStore?
	}
	a := f.action()
	r.registerAction(name, a)
	// TODO(jba): this is a roundabout way to transmit the tracing state. Is there a cleaner way?
	f.tstate = a.tstate
	r.registerFlow(f)
	return f
}

// TODO(jba): use flowError?

// A flowInstruction is an instruction to follow with a flow.
// It is the input for the flow's action.
// Exactly one field will be non-nil.
type flowInstruction[I any] struct {
	Start        *startInstruction[I]     `json:"start,omitempty"`
	Resume       *resumeInstruction       `json:"resume,omitempty"`
	Schedule     *scheduleInstruction[I]  `json:"schedule,omitempty"`
	RunScheduled *runScheduledInstruction `json:"runScheduled,omitempty"`
	State        *stateInstruction        `json:"state,omitempty"`
	Retry        *retryInstruction        `json:"retry,omitempty"`
}

// A startInstruction starts a flow.
type startInstruction[I any] struct {
	Input  I                 `json:"input,omitempty"`
	Labels map[string]string `json:"labels,omitempty"`
}

// A resumeInstruction resumes a flow that was started and then interrupted.
type resumeInstruction struct {
	FlowID  string `json:"flowId,omitempty"`
	Payload any    `json:"payload,omitempty"`
}

// A scheduleInstruction schedules a flow to start at a later time.
type scheduleInstruction[I any] struct {
	DelaySecs float64 `json:"delay,omitempty"`
	Input     I       `json:"input,omitempty"`
}

// A runScheduledInstruction starts a scheduled flow.
type runScheduledInstruction struct {
	FlowID string `json:"flowId,omitempty"`
}

// A stateInstruction retrieves the flowState from the flow.
type stateInstruction struct {
	FlowID string `json:"flowId,omitempty"`
}

// TODO(jba): document
type retryInstruction struct {
	FlowID string `json:"flowId,omitempty"`
}

// A flowState is a persistent representation of a flow that may be in the middle of running.
// It contains all the information needed to resume a flow, including the original input
// and a cache of all completed steps.
type flowState[I, O any] struct {
	FlowID   string `json:"flowId,omitempty"`
	FlowName string `json:"name,omitempty"`
	// start time in milliseconds since the epoch
	StartTime tracing.Milliseconds `json:"startTime,omitempty"`
	Input     I                    `json:"input,omitempty"`

	mu              sync.Mutex
	Cache           map[string]json.RawMessage `json:"cache,omitempty"`
	EventsTriggered map[string]any             `json:"eventsTriggered,omitempty"`
	Executions      []*flowExecution           `json:"executions,omitempty"`
	// The operation is the user-visible part of the state.
	Operation    *operation[O] `json:"operation,omitempty"`
	TraceContext string        `json:"traceContext,omitempty"`
}

func newFlowState[I, O any](id, name string, input I) *flowState[I, O] {
	return &flowState[I, O]{
		FlowID:    id,
		FlowName:  name,
		Input:     input,
		StartTime: tracing.ToMilliseconds(time.Now()),
		Cache:     map[string]json.RawMessage{},
		Operation: &operation[O]{
			FlowID: id,
			Done:   false,
		},
	}
}

// flowStater is the common type of all flowState[I, O] types.
type flowStater interface {
	isFlowState()
	lock()
	unlock()
	cache() map[string]json.RawMessage
}

// isFlowState implements flowStater.
func (fs *flowState[I, O]) isFlowState()                      {}
func (fs *flowState[I, O]) lock()                             { fs.mu.Lock() }
func (fs *flowState[I, O]) unlock()                           { fs.mu.Unlock() }
func (fs *flowState[I, O]) cache() map[string]json.RawMessage { return fs.Cache }

// An operation describes the state of a Flow that may still be in progress.
type operation[O any] struct {
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
	Metadata any            `json:"metadata,omitempty"`
	Result   *FlowResult[O] `json:"result,omitempty"`
}

// A FlowResult is the result of a flow: either success, in which case Response is
// the return value of the flow's function; or failure, in which case Error is the
// non-empty error string.
type FlowResult[Out any] struct {
	Response Out    `json:"response,omitempty"`
	Error    string `json:"error,omitempty"`
	// The Error field above is not used in the code, but it gets marshaled
	// into JSON.
	// TODO(jba): replace with  a type that implements error and json.Marshaler.
	err        error
	StackTrace string `json:"stacktrace,omitempty"`
}

// FlowResult is called FlowResponse in the javascript.

// action creates an action for the flow. See the comment at the top of this file for more information.
func (f *Flow[In, Out, Stream]) action() *Action[*flowInstruction[In], *flowState[In, Out], Stream] {
	var i In
	var o Out
	metadata := map[string]any{
		"inputSchema":  inferJSONSchema(i),
		"outputSchema": inferJSONSchema(o),
	}
	cback := func(ctx context.Context, inst *flowInstruction[In], cb func(context.Context, Stream) error) (*flowState[In, Out], error) {
		tracing.SetCustomMetadataAttr(ctx, "flow:wrapperAction", "true")
		return f.runInstruction(ctx, inst, streamingCallback[Stream](cb))
	}
	return NewStreamingAction(f.name, ActionTypeFlow, metadata, cback)
}

// runInstruction performs one of several actions on a flow, as determined by msg.
// (Called runEnvelope in the js.)
func (f *Flow[In, Out, Stream]) runInstruction(ctx context.Context, inst *flowInstruction[In], cb streamingCallback[Stream]) (*flowState[In, Out], error) {
	switch {
	case inst.Start != nil:
		// TODO(jba): pass msg.Start.Labels.
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

// flow is the type that all Flow[In, Out, Stream] have in common.
type flow interface {
	Name() string

	// runJSON uses encoding/json to unmarshal the input,
	// calls Flow.start, then returns the marshaled result.
	runJSON(ctx context.Context, input json.RawMessage, cb streamingCallback[json.RawMessage]) (json.RawMessage, error)
}

func (f *Flow[In, Out, Stream]) Name() string { return f.name }

func (f *Flow[In, Out, Stream]) runJSON(ctx context.Context, input json.RawMessage, cb streamingCallback[json.RawMessage]) (json.RawMessage, error) {
	var in In
	if err := json.Unmarshal(input, &in); err != nil {
		return nil, &httpError{http.StatusBadRequest, err}
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
			// TODO(jba): do something more with this error?
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
	// TODO(jba): retrieve the JSON-marshaled SpanContext from state.traceContext.
	// TODO(jba): add a span link to the context.
	output, err := tracing.RunInNewSpan(ctx, fctx.tracingState(), f.name, "flow", true, state.Input, func(ctx context.Context, input In) (Out, error) {
		tracing.SetCustomMetadataAttr(ctx, "flow:execution", strconv.Itoa(len(state.Executions)-1))
		// TODO(jba): put labels into span metadata.
		tracing.SetCustomMetadataAttr(ctx, "flow:name", f.name)
		tracing.SetCustomMetadataAttr(ctx, "flow:id", state.FlowID)
		tracing.SetCustomMetadataAttr(ctx, "flow:dispatchType", dispatchType)
		rootSpanContext := otrace.SpanContextFromContext(ctx)
		traceID := rootSpanContext.TraceID().String()
		exec.TraceIDs = append(exec.TraceIDs, traceID)
		// TODO(jba): Save rootSpanContext in the state.
		// TODO(jba): If input is missing, get it from state.input and overwrite metadata.input.
		start := time.Now()
		output, err := f.fn(ctx, input, cb)
		latency := time.Since(start)
		if err != nil {
			// TODO(jba): handle InterruptError
			logger.FromContext(ctx).Error("flow failed",
				"path", tracing.SpanPath(ctx),
				"err", err.Error(),
			)
			writeFlowFailure(ctx, f.name, latency, err)
			tracing.SetCustomMetadataAttr(ctx, "flow:state", "error")
		} else {
			logger.FromContext(ctx).Info("flow succeeded", "path", tracing.SpanPath(ctx))
			writeFlowSuccess(ctx, f.name, latency)
			tracing.SetCustomMetadataAttr(ctx, "flow:state", "done")

		}
		// TODO(jba): telemetry
		return output, err
	})
	// TODO(jba): perhaps this should be in a defer, to handle panics?
	state.mu.Lock()
	defer state.mu.Unlock()
	state.Operation.Done = true
	if err != nil {
		state.Operation.Result = &FlowResult[Out]{
			err:   err,
			Error: err.Error(),
			// TODO(jba): stack trace?
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
	stateStore FlowStateStore
	tstate     *tracing.State
	mu         sync.Mutex
	seenSteps  map[string]int // number of times each name appears, to avoid duplicate names
	// TODO(jba): auth
}

// flowContexter is the type of all flowContext[I, O].
type flowContexter interface {
	uniqueStepName(string) string
	stater() flowStater
	tracingState() *tracing.State
}

func newFlowContext[I, O any](state *flowState[I, O], store FlowStateStore, tstate *tracing.State) *flowContext[I, O] {
	return &flowContext[I, O]{
		state:      state,
		stateStore: store,
		tstate:     tstate,
		seenSteps:  map[string]int{},
	}
}
func (fc *flowContext[I, O]) stater() flowStater           { return fc.state }
func (fc *flowContext[I, O]) tracingState() *tracing.State { return fc.tstate }

// finish is called at the end of a flow execution.
func (fc *flowContext[I, O]) finish(ctx context.Context) error {
	if fc.stateStore == nil {
		return nil
	}
	// TODO(jba): In the js, start saves the state only under certain conditions. Duplicate?
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

var flowContextKey = internal.NewContextKey[flowContexter]()

// Run runs the function f in the context of the current flow.
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
	// TODO(jba): The input here is irrelevant. Perhaps runInNewSpan should have only a result type param,
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
		// TODO(jba): don't memoize a nested flow (see context.ts)
		fs := fc.stater()
		fs.lock()
		j, ok := fs.cache()[uName]
		fs.unlock()
		if ok {
			var t Out
			if err := json.Unmarshal(j, &t); err != nil {
				return internal.Zero[Out](), err
			}
			tracing.SetCustomMetadataAttr(ctx, "flow:state", "cached")
			return t, nil
		}
		t, err := f()
		if err != nil {
			return internal.Zero[Out](), err
		}
		bytes, err := json.Marshal(t)
		if err != nil {
			return internal.Zero[Out](), err
		}
		fs.lock()
		fs.cache()[uName] = json.RawMessage(bytes)
		fs.unlock()
		tracing.SetCustomMetadataAttr(ctx, "flow:state", "run")
		return t, nil
	})
}

// RunFlow runs flow in the context of another flow. The flow must run to completion when started
// (that is, it must not have interrupts).
func RunFlow[In, Out, Stream any](ctx context.Context, flow *Flow[In, Out, Stream], input In) (Out, error) {
	state, err := flow.start(ctx, input, nil)
	if err != nil {
		return internal.Zero[Out](), err
	}
	return finishedOpResponse(state.Operation)
}

// InternalStreamFlow is for use by genkit.StreamFlow exclusively.
// It is not subject to any backwards compatibility guarantees.
func InternalStreamFlow[In, Out, Stream any](ctx context.Context, flow *Flow[In, Out, Stream], input In, callback func(context.Context, Stream) error) (Out, error) {

	state, err := flow.start(ctx, input, callback)
	if err != nil {
		return internal.Zero[Out](), err
	}
	if ctx.Err() != nil {
		return internal.Zero[Out](), ctx.Err()
	}
	return finishedOpResponse(state.Operation)
}

func finishedOpResponse[O any](op *operation[O]) (O, error) {
	if !op.Done {
		return internal.Zero[O](), fmt.Errorf("flow %s did not finish execution", op.FlowID)
	}
	if op.Result.err != nil {
		return internal.Zero[O](), fmt.Errorf("flow %s: %w", op.FlowID, op.Result.err)
	}
	return op.Result.Response, nil
}
