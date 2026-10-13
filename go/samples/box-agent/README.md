# Genkit in a Box: a boxed agent

The whole agent (model calls, the `takeNote` tool, conversation state) lives in
[`boxed/`](boxed/main.go), one process per chat session. This program holds no
model and no tools; it only routes. `box.DefineAgent` registers the boxed agent
here, so it shows up and is chattable in the Dev UI like a local one.

## Run

```bash
export GEMINI_API_KEY=...
genkit start -- go run .
```

The first session's box is built by `go run ./boxed`, which can take a moment.

- Chat with `notesAgent` in the Dev UI and tell it something worth remembering;
  `takeNote` reports its pid. Start a second session: a different pid, its own
  box process.
- Call `chatWithNotes` with `{"sessionId": "s1", "message": "remember to buy milk"}`,
  the way an app backend would: it streams the reply with `AgentHandle.StreamText`.
  Repeat with the same `sessionId` and the notes accumulate.

## How it routes

```go
box.New(g, box.ExecRunner(box.Cmd("go", "run", "./boxed")),
	box.WithRoute(box.SessionRoute),      // one box per session
	box.WithIdleTimeout(10*time.Minute), // release an idle session's box
)
```

`SessionRoute` reads the session from the agent's init, which the Dev UI and
`aix.WithSessionID` send. A call that names no session (a later Dev UI turn
resuming by snapshot alone) goes to a shared box. The boxed agent uses a
`FileSessionStore` that every box reads, so whichever box gets a turn continues
the conversation: routing decides placement, the store decides survival.
