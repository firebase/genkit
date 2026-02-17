# Subagent Middleware Design (Conceptual, Simplified)

Status: proposal only. This document focuses on the critical path and intentionally drops non-essential complexity.

## Why Not `WrapGenerate` for Dispatch

Short answer: in current `ai.Generate` flow, `WrapGenerate` is the wrong interception point for model tool calls.

In `go/ai/generate.go`, the model call and tool execution loop are inside the `generate(...)` function. `WrapGenerate` wraps each iteration of that function, but by the time `next(...)` returns to `WrapGenerate`, tool calls have already been handled (unless `ReturnToolRequests` is on, which changes global behavior).

So `WrapGenerate` can:

- See/modify the request before model execution.
- See the final iteration response.

But `WrapGenerate` cannot naturally own per-tool dispatch semantics without re-implementing the internal tool loop.

The clean interception point for delegated subagent execution is still tool execution (`WrapTool`), even if we use a single synthetic tool like `call_subagent`.

## Simplified Architecture

Use one universal middleware-injected tool:

- Tool name: `call_subagent` (configurable).
- Model asks for this tool with `{agent, messages}` payload.
- Middleware intercepts this tool in `WrapTool` and routes to the configured child agent.

This keeps delegation explicit, simple, and model-visible.

## Reference Session-Flow Contract

Session flows in `/Users/alex/Developer/genkit-super/genkit-read-only/go/ai/x/session_flow.go` emit:

- Input: `SessionFlowInput{Messages}`
- Stream chunk envelope: `{Chunk, Status, Artifact, SnapshotCreated, EndTurn}`
- Final output: `{State, SnapshotID}`

For this design, we only fold:

- `messages`
- `artifacts`

No custom-state fold modes.

## Proposed Middleware Surface

```go
type Subagent struct {
  ai.BaseMiddleware

  // Single universal delegation tool name.
  ToolName string `json:"toolName,omitempty"` // default: "call_subagent"

  // Agent routing table keyed by logical agent id.
  Agents map[string]SubagentTarget `json:"agents,omitempty"`

  // Forward child model chunks to parent stream.
  StreamChildren bool `json:"streamChildren,omitempty"`

  // Recursion guard.
  MaxDepth int `json:"maxDepth,omitempty"`
}

type SubagentTarget struct {
  Kind   string `json:"kind"`   // "generate" | "prompt" | "sessionFlow"
  Target string `json:"target"` // model/prompt/flow name
}

type CallSubagentInput struct {
  Agent    string        `json:"agent"`
  Messages []*ai.Message `json:"messages,omitempty"`
}

type SubagentFold struct {
  Messages  []*ai.Message            `json:"messages,omitempty"`
  Artifacts []*aix.SessionFlowArtifact `json:"artifacts,omitempty"`
}
```

## Critical Path

1. Middleware injects one tool (`call_subagent`) via `Tools()`.
2. Parent model requests that tool with `{agent, messages}`.
3. `WrapTool` intercepts the tool call and executes selected child target.
4. Child emits stream chunks (optional passthrough to parent stream).
5. Middleware builds a fold object with only `messages` and `artifacts`.
6. Middleware returns `ToolResponse` where:
   - `Output` contains child result + fold payload.
   - `Content` contains compact natural-language summary for parent model.
7. Parent model continues normal tool loop with this tool response.

## Pseudocode (Dispatch)

```go
func (m *Subagent) WrapTool(ctx context.Context, p *ai.ToolParams, next ai.ToolNext) (*ai.ToolResponse, error) {
  toolName := m.ToolName
  if toolName == "" {
    toolName = "call_subagent"
  }
  if p.Request.Name != toolName {
    return next(ctx, p)
  }

  if overDepth(ctx, m.MaxDepth) {
    return nil, core.NewError(core.ABORTED, "subagent: max depth exceeded")
  }

  in := decodeCallSubagentInput(p.Request.Input) // {agent,messages}
  target, ok := m.Agents[in.Agent]
  if !ok {
    return nil, core.NewError(core.NOT_FOUND, "subagent: unknown agent %q", in.Agent)
  }

  result, fold, err := m.runChild(ctx, target, in, p)
  if err != nil {
    return nil, err
  }

  return &ai.ToolResponse{
    Name: p.Request.Name,
    Output: map[string]any{
      "agent": in.Agent,
      "result": result,
      "fold": fold, // messages + artifacts only
    },
    Content: []*ai.Part{
      ai.NewTextPart(summaryForParent(result, fold)),
    },
  }, nil
}
```

## Pseudocode (Session-Flow Child)

```go
func (m *Subagent) runSessionFlowChild(...) (result any, fold *SubagentFold, err error) {
  conn, err := lookupSessionFlow(target).StreamBidi(ctx)
  if err != nil {
    return nil, nil, err
  }
  defer conn.Close()

  _ = conn.Send(&aix.SessionFlowInput{Messages: in.Messages})

  fold = &SubagentFold{}
  for ch, err := range conn.Receive() {
    if err != nil {
      return nil, nil, err
    }
    if m.StreamChildren && ch.Chunk != nil {
      _ = emitParentChunk(ctx, ch.Chunk) // requires runtime hook, see gaps
    }
    if ch.Artifact != nil {
      fold.Artifacts = append(fold.Artifacts, ch.Artifact)
    }
    if ch.EndTurn {
      break
    }
  }

  out, err := conn.Output()
  if err != nil {
    return nil, nil, err
  }
  fold.Messages = out.State.Messages
  // artifacts in out.State.Artifacts can be used as canonical deduped final set
  if len(out.State.Artifacts) > 0 {
    fold.Artifacts = out.State.Artifacts
  }
  return out, fold, nil
}
```

## What Was Removed to Simplify

Removed from prior design:

- Per-delegate tool names.
- Fold mode matrix (`tool-output` vs `state-bridge`).
- Custom-state folding.
- Typed status/snapshot event streaming as first-class requirement.

Kept:

- One universal delegation tool.
- Route table (`agent` -> target).
- Optional child chunk passthrough.
- Canonical fold of messages + artifacts only.

## Minimal Runtime Gaps to Close

### 1) Stream passthrough from tool middleware

Current `ToolParams` has no parent stream emitter. Add:

```go
EmitChunk func(context.Context, *ai.ModelResponseChunk) error
```

Wire from `handleToolRequests` -> `runToolWithMiddleware`.

Without this, child chunk passthrough cannot happen from `WrapTool`.

### 2) Flow/session-flow lookup API for middleware

Middleware currently can look up models via `genkit.FromContext(ctx)` + `LookupModel`, but no equivalent flow/session-flow lookup helper exists for middleware packages.

Add a minimal public lookup path for flow/session-flow actions.

### 3) Bidi/runtime availability

Current `genkit` core branch does not include the bidi/session-flow primitives present in `genkit-read-only`. Session-flow routing should be feature-gated until those primitives land.

## Recommended Rollout

### Phase 1 (works on current architecture)

- Single `call_subagent` tool.
- Route only to `generate` and `prompt` child targets.
- Fold only messages/artifacts into tool output payload.
- No child stream passthrough yet.

### Phase 2

- Enable session-flow routes once bidi primitives are in `genkit`.
- Add `EmitChunk` hook and stream child model chunks to parent stream.

## Clarifying Questions

1. Do you want `call_subagent` to accept raw `messages`, or a smaller `{goal, context}` payload that middleware converts to messages?
2. Should folded artifacts use final canonical state only (`out.State.Artifacts`) or include per-chunk artifact events as well?
3. For Phase 1, is no child stream passthrough acceptable until `EmitChunk` support is added?
