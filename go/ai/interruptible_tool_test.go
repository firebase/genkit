// Copyright 2026 Google LLC
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

// Tests for the interruptible tool surface of tools.go that drive tools the
// way callers do, through the ai/tool runtime verbs. They live in package
// ai_test rather than in tools_test.go because ai/tool imports ai: an internal
// test file importing it would close an import cycle, so the external test
// package is the escape hatch.
package ai_test

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"reflect"
	"strings"
	"sync"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/ai/tool"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/status"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/google/go-cmp/cmp"
)

// newToolTestRegistry returns a registry with the formats and generate action
// configured, ready for ai.Generate / ai.GenerateStream.
func newToolTestRegistry(t *testing.T) *registry.Registry {
	t.Helper()
	reg := registry.New()
	ai.ConfigureFormats(reg)
	ai.DefineGenerateAction(context.Background(), reg)
	return reg
}

// defineTestModel builds and registers a model, the two steps
// genkit.DefineModel fuses for an application.
func defineTestModel(reg api.Registry, name string, opts *ai.ModelOptions, fn ai.ModelFunc) ai.Model {
	m := ai.NewModel(name, opts, fn)
	m.Register(reg)
	return m
}

// defineTestTool builds and registers a tool written against ai.ToolContext
// from a function that only wants a context.Context. The adapter is what
// makes these tests double as coverage that the ai/tool verbs work from a
// ToolContext tool: the context they receive is the ToolContext itself.
func defineTestTool[In, Out any](reg api.Registry, name, description string, fn func(context.Context, In) (Out, error)) *ai.ToolAction[In, Out] {
	tl := ai.NewTool(name, description, func(tc *ai.ToolContext, in In) (Out, error) {
		return fn(tc, in)
	})
	tl.Register(reg)
	return tl
}

// defineTestInterruptibleTool builds and registers an interruptible tool, the
// two steps genkit.DefineInterruptibleTool fuses for an application.
func defineTestInterruptibleTool[In, Out, Res any](reg api.Registry, name, description string, fn ai.InterruptibleToolFunc[In, Out, Res], opts ...ai.ToolOption) *ai.InterruptibleToolAction[In, Out, Res] {
	tl := ai.NewInterruptibleTool(name, description, fn, opts...)
	tl.Register(reg)
	return tl
}

// defineToolThenFinishModel defines "test/model": on the first turn it returns
// reqs (typically tool requests), and once a tool response is in history it
// returns the final text "done". This drives a single tool round per Generate.
func defineToolThenFinishModel(reg *registry.Registry, reqs ...*ai.Part) {
	defineTestModel(reg, "test/model",
		&ai.ModelOptions{Supports: &ai.ModelSupports{Multiturn: true, Tools: true}},
		func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
			for _, m := range req.Messages {
				if m.Role == ai.RoleTool {
					return &ai.ModelResponse{
						Request:      req,
						Message:      ai.NewModelTextMessage("done"),
						FinishReason: ai.FinishReasonStop,
					}, nil
				}
			}
			return &ai.ModelResponse{
				Request:      req,
				Message:      &ai.Message{Role: ai.RoleModel, Content: reqs},
				FinishReason: ai.FinishReasonStop,
			}, nil
		})
}

type weatherIn struct {
	City string `json:"city"`
}

// TestTool_AttachParts verifies AttachParts folds extra content into the tool's
// multipart response without changing the function signature, for a tool
// written against ToolContext.
func TestTool_AttachParts(t *testing.T) {
	reg := newToolTestRegistry(t)
	shot := defineTestTool(reg, "screenshot", "takes a screenshot",
		func(ctx context.Context, _ struct{}) (string, error) {
			// A nil part is ignored, so a failed constructor result can be
			// passed without a check.
			tool.AttachParts(ctx, nil, ai.NewMediaPart("image/png", "pngbytes"))
			return "captured", nil
		})

	resp, err := shot.RunRawMultipart(context.Background(), struct{}{})
	if err != nil {
		t.Fatalf("RunRawMultipart: %v", err)
	}
	if resp.Output != "captured" {
		t.Errorf("output = %v, want %q", resp.Output, "captured")
	}
	if len(resp.Content) != 1 || !resp.Content[0].IsMedia() {
		t.Fatalf("expected one attached media part, got %+v", resp.Content)
	}
}

// TestMultipartTool_AttachParts verifies attached parts are appended to the
// content a multipart tool returns itself, rather than replacing it.
func TestMultipartTool_AttachParts(t *testing.T) {
	tl := ai.NewMultipartTool("chart", "charts and annotates",
		func(tc *ai.ToolContext, _ struct{}) (*ai.MultipartToolResponse, error) {
			tool.AttachParts(tc, ai.NewMediaPart("image/png", "annotation"))
			return &ai.MultipartToolResponse{
				Output:  "charted",
				Content: []*ai.Part{ai.NewMediaPart("image/png", "chart")},
			}, nil
		})

	resp, err := tl.RunRawMultipart(context.Background(), struct{}{})
	if err != nil {
		t.Fatalf("RunRawMultipart: %v", err)
	}
	if len(resp.Content) != 2 || resp.Content[0].Text != "chart" || resp.Content[1].Text != "annotation" {
		t.Fatalf("content = %+v, want the returned part followed by the attached one", resp.Content)
	}

	// A multipart function may return no response at all; the attached parts
	// still need somewhere to land.
	silent := ai.NewMultipartTool("silent", "attaches, returns nothing",
		func(tc *ai.ToolContext, _ struct{}) (*ai.MultipartToolResponse, error) {
			tool.AttachParts(tc, ai.NewMediaPart("image/png", "only"))
			return nil, nil
		})
	resp, err = silent.RunRawMultipart(context.Background(), struct{}{})
	if err != nil {
		t.Fatalf("RunRawMultipart: %v", err)
	}
	if len(resp.Content) != 1 || resp.Content[0].Text != "only" {
		t.Fatalf("content = %+v, want the attached part on an empty response", resp.Content)
	}
}

type reportItem struct {
	Name string `json:"name"`
}

type reportOut struct {
	Title string       `json:"title"`
	Items []reportItem `json:"items"`
}

// TestInterruptibleTool_OutputSchemaMatchesNewTool guards against the multipart
// envelope leaking into the tool definition: an interruptible tool must
// advertise the same output schema NewTool would for the same Out, including a
// pointer Out (whose zero value is a nil pointer) and a nested struct that
// exercises schema inlining.
func TestInterruptibleTool_OutputSchemaMatchesNewTool(t *testing.T) {
	classic := ai.NewTool("classic", "d",
		func(tc *ai.ToolContext, _ weatherIn) (reportOut, error) { return reportOut{}, nil })
	want := classic.Definition().OutputSchema
	if want == nil {
		t.Fatal("ai.NewTool unexpectedly produced a nil output schema")
	}

	interruptible := ai.NewInterruptibleTool("interruptible", "d",
		func(ctx context.Context, _ weatherIn, _ *confirmation) (reportOut, error) { return reportOut{}, nil })
	pointer := ai.NewInterruptibleTool("pointer", "d",
		func(ctx context.Context, _ weatherIn, _ *confirmation) (*reportOut, error) { return nil, nil })

	for _, tc := range []struct {
		name string
		got  any
	}{
		{"struct output", interruptible.Definition().OutputSchema},
		{"pointer output", pointer.Definition().OutputSchema},
	} {
		if !reflect.DeepEqual(tc.got, want) {
			t.Errorf("%s output schema = %#v\nwant %#v (matching ai.NewTool)", tc.name, tc.got, want)
		}
		props, _ := tc.got.(map[string]any)["properties"].(map[string]any)
		if _, ok := props["title"]; !ok {
			t.Errorf("%s output schema missing the real %q field: %#v", tc.name, "title", tc.got)
		}
		if _, ok := props["content"]; ok {
			t.Errorf("%s output schema leaked the multipart envelope (has %q): %#v", tc.name, "content", tc.got)
		}
	}
}

// TestInterruptibleTool_OutputSchemaSurvivesLookup is the test that matters for
// what the model actually receives: the generate loop resolves tools by name
// out of the registry, so the real output schema has to survive that type
// erasure.
func TestInterruptibleTool_OutputSchemaSurvivesLookup(t *testing.T) {
	reg := newToolTestRegistry(t)

	var gotTools []*ai.ToolDefinition
	defineTestModel(reg, "test/model",
		&ai.ModelOptions{Supports: &ai.ModelSupports{Multiturn: true, Tools: true}},
		func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
			gotTools = req.Tools
			return &ai.ModelResponse{
				Request:      req,
				Message:      ai.NewModelTextMessage("done"),
				FinishReason: ai.FinishReasonStop,
			}, nil
		})

	report := defineTestInterruptibleTool(reg, "report", "builds a report",
		func(ctx context.Context, _ weatherIn, _ *confirmation) (reportOut, error) { return reportOut{}, nil })

	if _, err := ai.Generate(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithPrompt("report"),
		ai.WithTools(report)); err != nil {
		t.Fatalf("Generate: %v", err)
	}

	if len(gotTools) != 1 {
		t.Fatalf("model saw %d tools, want 1", len(gotTools))
	}
	props, _ := gotTools[0].OutputSchema["properties"].(map[string]any)
	if _, ok := props["title"]; !ok {
		t.Errorf("model saw output schema %#v, want the real Out type", gotTools[0].OutputSchema)
	}
	if _, ok := props["content"]; ok {
		t.Errorf("model saw the multipart envelope as the output schema: %#v", gotTools[0].OutputSchema)
	}
}

// TestInterruptibleTool_OutputSchemaOptions pins that NewInterruptibleTool
// runs the output schema check NewTool runs (tools_test.go covers the option
// itself; both constructors share newTool): with a concrete Out the
// constructor panics, naming itself, rather than advertising a schema that
// disagrees with the type.
func TestInterruptibleTool_OutputSchemaOptions(t *testing.T) {
	defer func() {
		r := recover()
		if r == nil {
			t.Fatal("expected panic for an output schema option with concrete Out")
		}
		err, ok := r.(error)
		if !ok || !strings.Contains(err.Error(), "ai.NewInterruptibleTool") {
			t.Errorf("panic = %v, want it to name ai.NewInterruptibleTool", r)
		}
	}()
	ai.NewInterruptibleTool("t", "d",
		func(ctx context.Context, input any, res *struct{}) (string, error) { return "", nil },
		ai.WithOutputSchemaName("Answer"))
}

// TestTool_SendPartialNoOpWithoutStreaming confirms SendPartial is a safe no-op
// when no streaming callback is wired (here, a direct RunRaw).
func TestTool_SendPartialNoOpWithoutStreaming(t *testing.T) {
	reg := newToolTestRegistry(t)
	tl := defineTestTool(reg, "noop", "streams when it can",
		func(ctx context.Context, _ struct{}) (string, error) {
			tool.SendPartial(ctx, map[string]any{"progress": 50})
			return "ok", nil
		})

	out, err := tl.RunRaw(context.Background(), struct{}{})
	if err != nil {
		t.Fatalf("RunRaw: %v", err)
	}
	if out != "ok" {
		t.Errorf("output = %v, want %q", out, "ok")
	}
}

type transferIn struct {
	Amount float64 `json:"amount"`
}
type transferOut struct {
	Status string `json:"status"`
}
type transferInterrupt struct {
	Reason string  `json:"reason"`
	Amount float64 `json:"amount"`
}
type confirmation struct {
	Approved bool `json:"approved"`
}

// interruptOnce returns an interruptible tool that pauses on its first pass and
// records what it saw when it re-executes, plus accessors for those recordings.
func interruptOnce(t *testing.T, reg *registry.Registry) (
	*ai.InterruptibleToolAction[transferIn, transferOut, confirmation],
	func() (*confirmation, transferIn, any),
) {
	t.Helper()
	var (
		gotResume   *confirmation
		gotInput    transferIn
		gotOriginal any
	)
	tl := defineTestInterruptibleTool(reg, "transfer", "transfers money",
		func(ctx context.Context, in transferIn, res *confirmation) (transferOut, error) {
			if res == nil {
				return transferOut{}, tool.Interrupt(ctx, transferInterrupt{Reason: "large_amount", Amount: in.Amount})
			}
			gotResume, gotInput = res, in
			if orig, ok := tool.OriginalInput[transferIn](ctx); ok {
				gotOriginal = orig
			}
			if !res.Approved {
				return transferOut{Status: "cancelled"}, nil
			}
			return transferOut{Status: "completed"}, nil
		})
	return tl, func() (*confirmation, transferIn, any) { return gotResume, gotInput, gotOriginal }
}

// generateUntilInterrupt runs the first turn and returns the response plus its
// single interrupt part.
func generateUntilInterrupt(t *testing.T, reg *registry.Registry, tl ai.ToolRef) (*ai.ModelResponse, *ai.Part) {
	t.Helper()
	resp, err := ai.Generate(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithPrompt("transfer 200"),
		ai.WithTools(tl))
	if err != nil {
		t.Fatalf("Generate: %v", err)
	}
	interrupts := resp.Interrupts()
	if len(interrupts) != 1 {
		t.Fatalf("expected 1 interrupt, got %d (finish=%s)", len(interrupts), resp.FinishReason)
	}
	return resp, interrupts[0]
}

// resumeWith continues an interrupted generation with the given restart or
// response parts and returns the final text.
func resumeWith(t *testing.T, reg *registry.Registry, resp *ai.ModelResponse, tl ai.ToolRef, opt ai.GenerateOption) string {
	t.Helper()
	resp2, err := ai.Generate(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithMessages(resp.History()...),
		ai.WithTools(tl),
		opt)
	if err != nil {
		t.Fatalf("resume Generate: %v", err)
	}
	return resp2.Text()
}

func newTransferTestRegistry(t *testing.T) *registry.Registry {
	t.Helper()
	reg := newToolTestRegistry(t)
	defineToolThenFinishModel(reg, ai.NewToolRequestPart(&ai.ToolRequest{
		Name: "transfer", Input: map[string]any{"amount": 200},
	}))
	return reg
}

// claim is Interrupted with a failed claim fatal, for the tests that assert
// what follows the claim.
func claim[In, Out, Res any](t *testing.T, tl *ai.InterruptibleToolAction[In, Out, Res], part *ai.Part) *ai.InterruptedCall[In, Out, Res] {
	t.Helper()
	call, ok := tl.Interrupted(part)
	if !ok {
		t.Fatalf("%s.Interrupted did not claim the tool's own interrupt", tl.Name())
	}
	return call
}

// TestInterruptibleTool_TypedRestart pins the core interrupt/resume contract:
// the tool interrupts with typed data on the first pass, the caller claims the
// part with Interrupted and reads the input typed, reads the interrupt data
// with ai.InterruptAs, restarts with a typed value, and the value reaches the
// function's *Res parameter on re-execution.
func TestInterruptibleTool_TypedRestart(t *testing.T) {
	reg := newTransferTestRegistry(t)
	transfer, recorded := interruptOnce(t, reg)
	resp, interrupt := generateUntilInterrupt(t, reg, transfer)

	call := claim(t, transfer, interrupt)
	if call.Input.Amount != 200 {
		t.Errorf("call.Input = %+v, want the input decoded from the wire {200}", call.Input)
	}
	if call.Part == nil || !call.Part.IsInterrupt() {
		t.Errorf("call.Part = %+v, want the interrupted part", call.Part)
	}
	meta, ok := ai.InterruptAs[transferInterrupt](call.Part)
	if !ok {
		t.Fatal("InterruptAs failed to decode the typed interrupt data")
	}
	if meta.Reason != "large_amount" || meta.Amount != 200 {
		t.Errorf("interrupt data = %+v, want {large_amount 200}", meta)
	}

	restart := call.Restart(confirmation{Approved: true})
	if got := resumeWith(t, reg, resp, transfer, ai.WithResume(restart)); got != "done" {
		t.Errorf("final text after restart = %q, want %q", got, "done")
	}
	gotResume, _, _ := recorded()
	if gotResume == nil || !gotResume.Approved {
		t.Errorf("resumed tool saw %+v, want Approved=true", gotResume)
	}
}

// TestInterruptibleTool_BareRestart documents what a restart with the zero
// value delivers: the tool re-executes with a non-nil, zero-valued resume
// parameter, which is what makes a bare restart read as approval for tools
// that key on the presence of a resume.
func TestInterruptibleTool_BareRestart(t *testing.T) {
	reg := newTransferTestRegistry(t)
	transfer, recorded := interruptOnce(t, reg)
	resp, interrupt := generateUntilInterrupt(t, reg, transfer)

	restart := claim(t, transfer, interrupt).Restart(confirmation{})
	if got := resumeWith(t, reg, resp, transfer, ai.WithResume(restart)); got != "done" {
		t.Errorf("final text after bare restart = %q, want %q", got, "done")
	}

	gotResume, _, _ := recorded()
	if gotResume == nil {
		t.Fatal("a bare restart must still deliver a non-nil resume parameter")
	}
	if gotResume.Approved {
		t.Errorf("bare restart resume = %+v, want the zero value", *gotResume)
	}
}

// TestInterruptibleTool_RestartWithInput covers the caller revising the
// arguments before approving: the tool re-executes with the new input and can
// still read what it was originally called with.
func TestInterruptibleTool_RestartWithInput(t *testing.T) {
	reg := newTransferTestRegistry(t)
	transfer, recorded := interruptOnce(t, reg)
	resp, interrupt := generateUntilInterrupt(t, reg, transfer)

	restart := claim(t, transfer, interrupt).RestartWithInput(transferIn{Amount: 50}, confirmation{Approved: true})
	if got := resumeWith(t, reg, resp, transfer, ai.WithResume(restart)); got != "done" {
		t.Errorf("final text = %q, want %q", got, "done")
	}

	_, gotInput, gotOriginal := recorded()
	if gotInput.Amount != 50 {
		t.Errorf("re-executed tool saw amount %v, want the new input 50", gotInput.Amount)
	}
	orig, ok := gotOriginal.(transferIn)
	if !ok || orig.Amount != 200 {
		t.Errorf("tool.OriginalInput = %+v (%T), want transferIn{200}", gotOriginal, gotOriginal)
	}
}

// TestInterruptibleTool_Respond resolves an interrupt with a pre-computed
// result instead of re-executing the tool. The output is validated against the
// tool's advertised output schema on the way through, so this also covers the
// schema surviving the registry lookup.
func TestInterruptibleTool_Respond(t *testing.T) {
	reg := newTransferTestRegistry(t)
	transfer, recorded := interruptOnce(t, reg)
	resp, interrupt := generateUntilInterrupt(t, reg, transfer)

	response := claim(t, transfer, interrupt).Respond(transferOut{Status: "manually approved"})
	if got := resumeWith(t, reg, resp, transfer, ai.WithResume(response)); got != "done" {
		t.Errorf("final text after respond = %q, want %q", got, "done")
	}
	if gotResume, _, _ := recorded(); gotResume != nil {
		t.Error("Respond must resolve the interrupt without re-executing the tool")
	}
}

// TestPartToRestart_Flow covers the ai.Part verbs used by callers that don't
// have the tool value in scope (e.g. a UI handler holding only the part): they
// build the same parts as the typed verbs of a claimed call, so the loop run
// in TestInterruptibleTool_TypedRestart covers both.
func TestPartToRestart_Flow(t *testing.T) {
	reg := newTransferTestRegistry(t)
	transfer, _ := interruptOnce(t, reg)
	_, interrupt := generateUntilInterrupt(t, reg, transfer)
	call := claim(t, transfer, interrupt)

	restart, err := interrupt.ToToolRestart(confirmation{Approved: true})
	if err != nil {
		t.Fatalf("ToToolRestart: %v", err)
	}
	if diff := cmp.Diff(call.Restart(confirmation{Approved: true}), restart); diff != "" {
		t.Errorf("ToToolRestart differs from InterruptedCall.Restart (-typed +part):\n%s", diff)
	}

	response, err := interrupt.ToToolResponse(transferOut{Status: "manually approved"})
	if err != nil {
		t.Fatalf("ToToolResponse: %v", err)
	}
	if diff := cmp.Diff(call.Respond(transferOut{Status: "manually approved"}), response); diff != "" {
		t.Errorf("ToToolResponse differs from InterruptedCall.Respond (-typed +part):\n%s", diff)
	}
}

type question struct {
	Text string `json:"text"`
}

// newQuestionTool builds and registers the pure-question tool: it always
// pauses, without data, and the answer is its output.
func newQuestionTool(reg api.Registry) *ai.InterruptibleToolAction[question, string, struct{}] {
	return defineTestInterruptibleTool(reg, "askUser", "asks the user a question",
		func(ctx context.Context, _ question, _ *struct{}) (string, error) {
			return "", tool.Interrupt(ctx, nil)
		})
}

// TestInterruptibleTool_QuestionPattern covers a tool whose whole job is to
// ask: the model's input is the question, the interrupt carries no data of
// its own, and Respond on the claimed call is the answer the model then sees.
// A restart re-asks, which the loop reports rather than repeating silently.
func TestInterruptibleTool_QuestionPattern(t *testing.T) {
	reg := newToolTestRegistry(t)
	defineToolThenFinishModel(reg, ai.NewToolRequestPart(&ai.ToolRequest{
		Name: "askUser", Input: map[string]any{"text": "proceed?"},
	}))
	askUser := newQuestionTool(reg)

	resp, interrupt := generateUntilInterrupt(t, reg, askUser)
	call := claim(t, askUser, interrupt)
	if call.Input.Text != "proceed?" {
		t.Errorf("call.Input = %+v, want the question the model asked", call.Input)
	}
	if _, ok := ai.InterruptAs[map[string]any](interrupt); ok {
		t.Error("a question tool's interrupt must carry no data of its own")
	}

	if got := resumeWith(t, reg, resp, askUser, ai.WithResume(call.Respond("yes"))); got != "done" {
		t.Errorf("final text after respond = %q, want %q", got, "done")
	}

	_, err := ai.Generate(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithMessages(resp.History()...),
		ai.WithTools(askUser),
		ai.WithResume(call.Restart(struct{}{})))
	if !errors.Is(err, status.ErrFailedPrecondition) {
		t.Errorf("restarting a question tool: err = %v, want FAILED_PRECONDITION for the repeated interrupt", err)
	}
}

// TestWithResume_MixedKinds resumes two interrupts from one turn with a
// single WithResume: one restarted, one answered.
func TestWithResume_MixedKinds(t *testing.T) {
	reg := newToolTestRegistry(t)
	defineToolThenFinishModel(reg,
		ai.NewToolRequestPart(&ai.ToolRequest{Name: "transfer", Ref: "a", Input: map[string]any{"amount": 200}}),
		ai.NewToolRequestPart(&ai.ToolRequest{Name: "askUser", Ref: "b", Input: map[string]any{"text": "sure?"}}))
	transfer, recorded := interruptOnce(t, reg)
	askUser := newQuestionTool(reg)

	resp, err := ai.Generate(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithPrompt("go"),
		ai.WithTools(transfer, askUser))
	if err != nil {
		t.Fatalf("Generate: %v", err)
	}
	interrupts := resp.Interrupts()
	if len(interrupts) != 2 {
		t.Fatalf("got %d interrupts, want 2", len(interrupts))
	}

	var parts []*ai.Part
	for _, part := range interrupts {
		if call, ok := transfer.Interrupted(part); ok {
			parts = append(parts, call.Restart(confirmation{Approved: true}))
		}
		if call, ok := askUser.Interrupted(part); ok {
			parts = append(parts, call.Respond("yes"))
		}
	}
	if len(parts) != 2 {
		t.Fatalf("claimed %d parts, want each interrupt claimed by exactly one tool", len(parts))
	}

	resumed, err := ai.Generate(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithMessages(resp.History()...),
		ai.WithTools(transfer, askUser),
		ai.WithResume(parts...))
	if err != nil {
		t.Fatalf("resume Generate: %v", err)
	}
	if resumed.Text() != "done" {
		t.Errorf("final text = %q, want %q", resumed.Text(), "done")
	}
	if gotResume, _, _ := recorded(); gotResume == nil || !gotResume.Approved {
		t.Errorf("restarted tool saw %+v, want Approved=true", gotResume)
	}
}

// TestToolContextTool_InterruptAndResumeData covers the verbs from a tool
// written against ToolContext: it interrupts with tool.Interrupt and, when
// restarted, reads the typed answer with tool.ResumeData off the context it
// was given (the ToolContext itself).
func TestToolContextTool_InterruptAndResumeData(t *testing.T) {
	reg := newToolTestRegistry(t)
	defineToolThenFinishModel(reg, ai.NewToolRequestPart(&ai.ToolRequest{
		Name: "gate", Input: map[string]any{"amount": 200},
	}))

	var (
		gotResume confirmation
		gotOK     bool
	)
	gate := defineTestTool(reg, "gate", "interrupts once, then reads its resume data",
		func(ctx context.Context, in transferIn) (string, error) {
			res, ok := tool.ResumeData[confirmation](ctx)
			if !ok {
				return "", tool.Interrupt(ctx, transferInterrupt{Reason: "confirm", Amount: in.Amount})
			}
			gotResume, gotOK = res, ok
			return "ok", nil
		})

	resp, interrupt := generateUntilInterrupt(t, reg, gate)
	meta, ok := ai.InterruptAs[transferInterrupt](interrupt)
	if !ok || meta.Reason != "confirm" {
		t.Fatalf("InterruptAs = %+v, %v; want the typed interrupt data", meta, ok)
	}
	// A ToolContext tool is a ToolAction, whose resume type is a map.
	call := claim(t, gate, interrupt)
	if call.Input.Amount != 200 {
		t.Errorf("call.Input = %+v, want {200}", call.Input)
	}
	restart := call.Restart(map[string]any{"approved": true})
	if got := resumeWith(t, reg, resp, gate, ai.WithResume(restart)); got != "done" {
		t.Errorf("final text = %q, want %q", got, "done")
	}
	if !gotOK || !gotResume.Approved {
		t.Errorf("ResumeData = %+v, %v; want {true}, true", gotResume, gotOK)
	}
}

// TestInterrupted_ClaimsOnlyOwnUnresolvedInterrupts checks that Interrupted
// reports false for everything that is not an unresolved interrupt of the
// tool, and on a nil tool.
func TestInterrupted_ClaimsOnlyOwnUnresolvedInterrupts(t *testing.T) {
	mine := ai.NewInterruptibleTool("mine", "d",
		func(ctx context.Context, _ struct{}, _ *confirmation) (string, error) { return "", nil })

	foreign := ai.NewToolRequestPart(&ai.ToolRequest{Name: "other"})
	foreign.Interrupt = &ai.ToolInterrupt{}
	resolved := ai.NewToolRequestPart(&ai.ToolRequest{Name: "mine"})
	resolved.Interrupt = &ai.ToolInterrupt{Resolved: true}
	plain := ai.NewToolRequestPart(&ai.ToolRequest{Name: "mine"})

	for name, part := range map[string]*ai.Part{
		"another tool's interrupt": foreign,
		"a resolved interrupt":     resolved,
		"a plain tool request":     plain,
		"a text part":              ai.NewTextPart("hi"),
		"a nil part":               nil,
	} {
		if _, ok := mine.Interrupted(part); ok {
			t.Errorf("Interrupted claimed %s", name)
		}
	}

	own := ai.NewToolRequestPart(&ai.ToolRequest{Name: "mine"})
	own.Interrupt = &ai.ToolInterrupt{}
	if _, ok := mine.Interrupted(own); !ok {
		t.Error("Interrupted did not claim the tool's own interrupt")
	}
	var nilTool *ai.InterruptibleToolAction[struct{}, string, confirmation]
	if _, ok := nilTool.Interrupted(own); ok {
		t.Error("a nil tool claimed a part")
	}
}

// TestNewInterruptibleTool_RejectsNonObjectResumeType covers the documented
// constraint: resume data must serialize to a JSON object. A resume type that
// cannot is rejected at definition, which is what lets Restart on a claimed
// call return the part without an error.
func TestNewInterruptibleTool_RejectsNonObjectResumeType(t *testing.T) {
	defer func() {
		r := recover()
		if r == nil {
			t.Fatal("expected a panic defining a tool whose resume type is a string")
		}
		err, ok := r.(error)
		if !ok || !strings.Contains(err.Error(), "ai.NewInterruptibleTool") || !strings.Contains(err.Error(), "JSON object") {
			t.Errorf("panic = %v, want it to name ai.NewInterruptibleTool and the JSON object constraint", r)
		}
	}()
	ai.NewInterruptibleTool("scalar", "d",
		func(ctx context.Context, _ struct{}, _ *string) (string, error) { return "", nil })
}

// TestInterrupt_NonObjectData_ReturnsClearError covers the same constraint on
// the interrupt side: interrupting with a scalar fails the call with a clear
// error when the loop records the interrupt, for both kinds of tool.
func TestInterrupt_NonObjectData_ReturnsClearError(t *testing.T) {
	for _, tc := range []struct {
		name   string
		define func(reg *registry.Registry) ai.Tool
	}{
		{"interruptible", func(reg *registry.Registry) ai.Tool {
			return defineTestInterruptibleTool(reg, "bad", "interrupts with a scalar",
				func(ctx context.Context, _ struct{}, _ *struct{}) (string, error) {
					return "", tool.Interrupt(ctx, "not an object")
				})
		}},
		{"plain", func(reg *registry.Registry) ai.Tool {
			return defineTestTool(reg, "bad", "interrupts with a scalar",
				func(ctx context.Context, _ struct{}) (string, error) {
					return "", tool.Interrupt(ctx, "not an object")
				})
		}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			reg := newToolTestRegistry(t)
			tl := tc.define(reg)
			defineToolThenFinishModel(reg, ai.NewToolRequestPart(&ai.ToolRequest{Name: "bad", Input: map[string]any{}}))

			_, err := ai.Generate(context.Background(), reg,
				ai.WithModelName("test/model"),
				ai.WithPrompt("go"),
				ai.WithTools(tl))
			if err == nil {
				t.Fatal("expected an error interrupting with non-object data")
			}
			if !strings.Contains(err.Error(), "JSON object") {
				t.Errorf("error = %q, want it to mention the JSON object constraint", err)
			}
		})
	}
}

// TestRestart_UndecodableResumeFailsTheCall pins that a resume payload the tool
// can't read fails the call instead of silently arriving as a zero value.
func TestRestart_UndecodableResumeFailsTheCall(t *testing.T) {
	reg := newTransferTestRegistry(t)
	transfer, _ := interruptOnce(t, reg)
	resp, interrupt := generateUntilInterrupt(t, reg, transfer)

	// approved is a bool on confirmation; a string can't decode into it.
	restart, err := interrupt.ToToolRestart(map[string]any{"approved": "yes"})
	if err != nil {
		t.Fatalf("ToToolRestart: %v", err)
	}
	_, err = ai.Generate(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithMessages(resp.History()...),
		ai.WithTools(transfer),
		ai.WithResume(restart))
	if err == nil {
		t.Fatal("expected the resumed call to fail on undecodable resume data")
	}
	if !strings.Contains(err.Error(), "resume data") {
		t.Errorf("error = %q, want it to name the resume data", err)
	}
}

// TestSendPartial_StreamsPartialToolResponse asserts a tool's SendPartial calls
// arrive on the stream as partial tool responses, distinguishable via
// IsPartial / ToolResponses.
func TestSendPartial_StreamsPartialToolResponse(t *testing.T) {
	reg := newToolTestRegistry(t)
	defineToolThenFinishModel(reg, ai.NewToolRequestPart(&ai.ToolRequest{Name: "progressTool", Input: map[string]any{}}))

	defineTestTool(reg, "progressTool", "streams progress",
		func(ctx context.Context, _ struct{}) (string, error) {
			tool.SendPartial(ctx, map[string]any{"progress": 50})
			return "complete", nil
		})

	var partials []*ai.Part
	for val, err := range ai.GenerateStream(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithPrompt("go"),
		ai.WithTools(ai.ToolName("progressTool"))) {
		if err != nil {
			t.Fatalf("GenerateStream: %v", err)
		}
		if val.Done {
			continue
		}
		for _, p := range val.Chunk.ToolResponses() {
			if p.IsPartial() {
				partials = append(partials, p)
			}
		}
	}

	if len(partials) == 0 {
		t.Fatal("expected at least one partial tool response on the stream")
	}
	if partials[0].ToolResponse.Name != "progressTool" {
		t.Errorf("partial tool name = %q, want %q", partials[0].ToolResponse.Name, "progressTool")
	}
}

// TestConcurrentStreamingTools_NoDataRace is the regression for the streaming
// race: when a model emits multiple tool calls in one turn and more than one
// streams via SendPartial, the per-tool senders run on concurrent goroutines.
// They must be serialized so they don't race on the shared stream callback.
// Run under `go test -race` to detect a regression.
func TestConcurrentStreamingTools_NoDataRace(t *testing.T) {
	reg := newToolTestRegistry(t)
	defineToolThenFinishModel(reg,
		ai.NewToolRequestPart(&ai.ToolRequest{Name: "toolA", Input: map[string]any{}}),
		ai.NewToolRequestPart(&ai.ToolRequest{Name: "toolB", Input: map[string]any{}}))

	// A rendezvous so both tools enter their SendPartial loops at the same
	// time, maximizing the chance of overlapping callback invocations.
	var ready sync.WaitGroup
	ready.Add(2)
	start := make(chan struct{})
	go func() { ready.Wait(); close(start) }()

	streamer := func(ctx context.Context, _ struct{}) (string, error) {
		ready.Done()
		<-start
		for i := 0; i < 200; i++ {
			tool.SendPartial(ctx, map[string]any{"n": i})
		}
		return "ok", nil
	}
	defineTestTool(reg, "toolA", "streams", streamer)
	defineTestTool(reg, "toolB", "streams", streamer)

	for _, err := range ai.GenerateStream(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithPrompt("go"),
		ai.WithTools(ai.ToolName("toolA"), ai.ToolName("toolB"))) {
		if err != nil {
			t.Fatalf("GenerateStream: %v", err)
		}
	}
}

// TestInterruptibleTool_UnregisteredViaWithTools passes an interruptible tool
// created with ai.NewInterruptibleTool, never registered, straight to Generate.
// It is an ai.Tool, so the loop registers it for the call the way it does an
// unregistered ai.NewTool.
func TestInterruptibleTool_UnregisteredViaWithTools(t *testing.T) {
	reg := newToolTestRegistry(t)
	defineToolThenFinishModel(reg, ai.NewToolRequestPart(&ai.ToolRequest{Name: "unregistered", Input: map[string]any{"city": "Lima"}}))

	ran := false
	tl := ai.NewInterruptibleTool("unregistered", "d",
		func(ctx context.Context, in weatherIn, _ *confirmation) (reportOut, error) {
			ran = true
			return reportOut{}, nil
		})

	resp, err := ai.Generate(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithPrompt("weather"),
		ai.WithTools(tl))
	if err != nil {
		t.Fatalf("Generate: %v", err)
	}
	if !ran {
		t.Error("the unregistered interruptible tool did not run")
	}
	if got := resp.Text(); got != "done" {
		t.Errorf("Text() = %q, want done", got)
	}
}

// jsRestartOf builds the restart part the JS runtime's restartTool builds for
// an interrupted request: the interrupted part's metadata spread onto the
// restart, "interrupt" key included, with "resumed" added. It goes through
// JSON so the part is exactly what a peer runtime would send.
func jsRestartOf(t *testing.T, interrupt *ai.Part, resumed any) *ai.Part {
	t.Helper()
	raw, err := json.Marshal(interrupt)
	if err != nil {
		t.Fatalf("marshal interrupt: %v", err)
	}
	var wire map[string]any
	if err := json.Unmarshal(raw, &wire); err != nil {
		t.Fatalf("unmarshal interrupt: %v", err)
	}
	meta, _ := wire["metadata"].(map[string]any)
	if meta == nil {
		meta = map[string]any{}
		wire["metadata"] = meta
	}
	meta["resumed"] = resumed
	raw, err = json.Marshal(wire)
	if err != nil {
		t.Fatalf("marshal restart: %v", err)
	}
	var restart ai.Part
	if err := json.Unmarshal(raw, &restart); err != nil {
		t.Fatalf("unmarshal restart: %v", err)
	}
	return &restart
}

// TestResume_AcceptsJSRestartShape pins that a restart part still carrying
// the interrupt it resolves, the shape every JS client sends, resumes the
// tool: the restart supersedes the interrupt rather than conflicting with it.
func TestResume_AcceptsJSRestartShape(t *testing.T) {
	reg := newTransferTestRegistry(t)
	transfer, saw := interruptOnce(t, reg)
	resp, interrupt := generateUntilInterrupt(t, reg, transfer)

	restart := jsRestartOf(t, interrupt, map[string]any{"approved": true})
	if !restart.IsInterrupt() || !restart.IsRestart() {
		t.Fatalf("restart = %+v, want both the interrupt and the restart state lifted", restart)
	}

	if got := resumeWith(t, reg, resp, transfer, ai.WithResume(restart)); got != "done" {
		t.Errorf("Text() = %q, want done", got)
	}
	if res, _, _ := saw(); res == nil || !res.Approved {
		t.Errorf("tool saw resume = %+v, want approved", res)
	}
}

// TestResume_NonObjectResumeMarkers pins how a resumed marker Go cannot
// deliver as an object is read, matching the JS runtime's truthiness rule:
// false is not a resumption and the tool re-executes afresh; any other
// non-object value is a bare restart.
func TestResume_NonObjectResumeMarkers(t *testing.T) {
	t.Run("false re-executes without a resume payload", func(t *testing.T) {
		reg := newTransferTestRegistry(t)
		transfer, saw := interruptOnce(t, reg)
		resp, interrupt := generateUntilInterrupt(t, reg, transfer)

		resp2, err := ai.Generate(context.Background(), reg,
			ai.WithModelName("test/model"),
			ai.WithMessages(resp.History()...),
			ai.WithTools(transfer),
			ai.WithResume(jsRestartOf(t, interrupt, false)))
		// The tool saw no resume, so it interrupted again, which the loop
		// reports as a failed precondition next to the partial response.
		if !errors.Is(err, status.ErrFailedPrecondition) || resp2 == nil {
			t.Fatalf("resume Generate = (%v, %v), want the re-interrupted partial and FAILED_PRECONDITION", resp2, err)
		}
		if resp2.FinishReason != ai.FinishReasonInterrupted {
			t.Errorf("FinishReason = %q, want interrupted", resp2.FinishReason)
		}
		if res, _, _ := saw(); res != nil {
			t.Errorf("tool saw resume = %+v, want none", res)
		}
	})

	for _, marker := range []any{"approved", 1.0, []any{"a"}} {
		t.Run(fmt.Sprintf("%T is a bare restart", marker), func(t *testing.T) {
			reg := newTransferTestRegistry(t)
			transfer, saw := interruptOnce(t, reg)
			resp, interrupt := generateUntilInterrupt(t, reg, transfer)

			if got := resumeWith(t, reg, resp, transfer, ai.WithResume(jsRestartOf(t, interrupt, marker))); got != "done" {
				t.Errorf("Text() = %q, want done", got)
			}
			if res, _, _ := saw(); res == nil || res.Approved {
				t.Errorf("tool saw resume = %+v, want the zero value of a bare restart", res)
			}
		})
	}
}

// TestWithResume_NilPartIsReported pins that a nil in the resume list, which
// a deprecated verb returns for a part it cannot restart, is reported as such
// rather than as a part of the wrong kind.
func TestWithResume_NilPartIsReported(t *testing.T) {
	reg := newTransferTestRegistry(t)
	transfer, _ := interruptOnce(t, reg)
	resp, _ := generateUntilInterrupt(t, reg, transfer)

	_, err := ai.Generate(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithMessages(resp.History()...),
		ai.WithTools(transfer),
		ai.WithResume(nil))
	if err == nil || !strings.Contains(err.Error(), "part is nil") {
		t.Errorf("error = %v, want it to report the nil part", err)
	}
}

// TestInterruptAs_DecodesIntoAnyMatchingType pins that the interrupt data a
// tool sent as a struct reads back into any type with the same JSON shape,
// in process as well as after a wire hop: the loop records the data as the
// JSON object it serializes to, so a handler in another package with its own
// view of the payload decodes it either way.
func TestInterruptAs_DecodesIntoAnyMatchingType(t *testing.T) {
	type transferInterruptView struct {
		Reason string  `json:"reason"`
		Amount float64 `json:"amount"`
	}
	reg := newTransferTestRegistry(t)
	transfer, _ := interruptOnce(t, reg)
	_, interrupt := generateUntilInterrupt(t, reg, transfer)

	if _, ok := interrupt.Interrupt.Data.(map[string]any); !ok {
		t.Errorf("Interrupt.Data = %T, want the JSON object the tool's struct serializes to", interrupt.Interrupt.Data)
	}
	view, ok := ai.InterruptAs[transferInterruptView](interrupt)
	if !ok || view.Reason != "large_amount" || view.Amount != 200 {
		t.Errorf("InterruptAs[view] = (%+v, %v), want the payload decoded", view, ok)
	}
	same, ok := ai.InterruptAs[transferInterrupt](interrupt)
	if !ok || same.Reason != "large_amount" {
		t.Errorf("InterruptAs[same type] = (%+v, %v), want the payload decoded", same, ok)
	}
}

// TestResume_PayloadReachesEveryReaderAlike pins that one restart reads the
// same through every reader: a map restarted in process keeps its Go types
// in the tool's resume parameter, in tool.ResumeData and in ai.ResumedValue,
// rather than widening to float64 in one of them.
func TestResume_PayloadReachesEveryReaderAlike(t *testing.T) {
	reg := newToolTestRegistry(t)
	defineToolThenFinishModel(reg, ai.NewToolRequestPart(&ai.ToolRequest{Name: "count", Input: map[string]any{}}))

	var (
		paramType, dataType string
		viaValue            int
	)
	count := defineTestInterruptibleTool(reg, "count", "d",
		func(ctx context.Context, _ struct{}, res *map[string]any) (string, error) {
			if res == nil {
				return "", tool.Interrupt(ctx, nil)
			}
			paramType = fmt.Sprintf("%T", (*res)["n"])
			rd, _ := tool.ResumeData[map[string]any](ctx)
			dataType = fmt.Sprintf("%T", rd["n"])
			viaValue, _ = ai.ResumedValue[int](ctx, "n")
			return "ok", nil
		})

	resp, err := ai.Generate(context.Background(), reg,
		ai.WithModelName("test/model"),
		ai.WithPrompt("count"),
		ai.WithTools(count))
	if err != nil {
		t.Fatalf("Generate: %v", err)
	}
	interrupts := resp.Interrupts()
	if len(interrupts) != 1 {
		t.Fatalf("expected 1 interrupt, got %d", len(interrupts))
	}
	call := claim(t, count, interrupts[0])
	if got := resumeWith(t, reg, resp, count, ai.WithResume(call.Restart(map[string]any{"n": 5}))); got != "done" {
		t.Errorf("Text() = %q, want done", got)
	}
	if paramType != "int" || dataType != "int" || viaValue != 5 {
		t.Errorf("resume parameter saw %s, tool.ResumeData saw %s, ai.ResumedValue saw %d; want int, int, 5", paramType, dataType, viaValue)
	}
}
