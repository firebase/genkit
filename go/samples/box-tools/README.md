# Genkit in a Box: tools

One program defines a `runShell` tool and boxes it (`box.ExecRunner(box.Self())`),
while the model call and the Gemini API key stay in the main process. Only
`runShell` calls cross into the box.

## Run

```bash
export GEMINI_API_KEY=...
genkit start -- go run .
```

Then, in the Dev UI:

- Call the `runInBox` flow with `{"cmd": "echo $$"}`. The pid it prints is the
  box process, not the main one.
- Call it with `{"cmd": "echo key=$GEMINI_API_KEY demo=$BOX_DEMO"}`. The key is
  empty: the box is started with `box.InheritBase()` and only gets the env the
  host passes in.
- Call `codingAgent` with a question like "what OS am I on?"; when the model
  uses `runShell`, that call executes inside the box.
- Open a trace: the `runShell` span carries `genkit:metadata:box`, and
  `genkit:metadata:box:traceId` links it to the box's own trace.

## How self mode works

The runner re-runs this same program as the box. In that copy,
`box.ServeIfRuntime(ctx)` returns true after serving, so `main` stops there
instead of doing the caller's work. `box.IsRuntime()` lets the copy skip setup
it does not need, here the Google AI plugin it has no key for.
