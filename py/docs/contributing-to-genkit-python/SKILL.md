---
name: contributing-to-genkit-python
description: How the Genkit Python API is put together, the judgment calls a linter can't make for you, and how to write the PR. Read this before you add or change anything a user imports, calls, passes in, or gets back.
---

# Contributing to Genkit Python

## What makes something Genkit

The public API surface is the product. Keep it as small and tight as you can. Every name, argument and return type you add is something users learn, depend on, and can't easily lose. When someone reviews a change, they mostly ask four things:

- Is the surface still clean?
- Is it as tight as it can be?
- Does it read like Python?
- Is what it opens up safe? It should be thought through for what Genkit is today and where it's going, not just for the case in front of you.

If you can solve the problem without adding to the surface, do that. If you can't, add the smallest thing that leaves room to grow.

Your code is the app. A flow or a tool is your own function with a decorator on it, typed by its own annotations. Genkit shouldn't need a second config language or a parallel class hierarchy to understand what you wrote. A `.prompt` file and `define_prompt` produce the same object.

One way to call any model. `generate` looks the same whichever provider is behind it, and provider-specific features come in through that model's typed config, not a separate API. Switching models should mean changing the ref, not rewriting the call.

Everything you define, you can see and run. Every action is traced, takes and returns JSON, and shows up in the Dev UI where you can run it by hand. If a new feature can't be run from the Dev UI, or shows up in a trace as an opaque blob, it isn't done.

Genkit doesn't do things you didn't ask for. It sends what you wrote. Retry, fallback, approval and the like are middleware you opt into with `use=`, not behavior baked into the core.

A few small pieces that compose. Actions, middleware and plugins should cover most new features. If something truly needs a new kind of thing, that's a big decision, so treat it like one.

Safe in production by default. Secrets are redacted, errors are redacted at the edge, and prompt and reply text stay off spans unless someone turns them on.

The same ideas in every language, written the way that language writes them. The wire format, traces and `.prompt` files are shared across SDKs. The Python surface should read like Python.

## Start with the snippet

Before writing any code, write the thing a user would paste into their app. Use a real-ish domain (orders, a menu, a refund, not `foo`), number the steps, and put `# =>` under anything that comes back. Then write one line each for the ways it can go wrong: "unknown key raises `INVALID_ARGUMENT` naming the key", "the tool fails mid-turn, so you get `finish_reason == FAILED` and the history up to that point".

If the snippet is awkward to write, the API is awkward. Change the API. Don't explain it in the docs.

## How the pieces fit

Everything goes through `ai`. The registry is private; if you need to look something up, it's `ai.lookup_model`, `ai.lookup_tool`, `ai.lookup_value`. Experimental features live on `genkit.exp.Genkit`, which subclasses the stable one. The stable class never picks up experimental methods, so changing the import is how you opt in.

Modules are split by who's reading them. `genkit` is for people building an app. `genkit.model`, `genkit.embedder`, `genkit.evaluator` and `genkit.middleware` are for people writing one of those. `genkit.plugin_api` is for plugin packages. Every name has exactly one home. If you're tempted to re-export something "for convenience", it's probably in the wrong module.

Everything is an action: one input, one output, maybe chunks. The function a user writes takes one request. If it needs context, it says so with an annotation (`ToolContext[ChunkT]`, `FlowContext[ChunkT]`, `ModelContext`), and typed config comes in through `Request[Cfg]`. Types flow from those annotations. Nobody should have to write `Operation[ModelResponse]` on something Genkit just handed them.

Models are referenced through plugin classmethods: `GoogleAI.gemini('gemini-flash-latest')` gives you a `ModelRef[GeminiConfig]`. There's one flat config class per model family. Passing a dict also works, and it gets validated into that same class.

If something's wrong before the run starts (bad config, unknown model), raise `GenkitError`. Once the run has started, don't raise. Return the response with `finish_reason`, a `Failure` on `.error`, and `messages` the user can send back to pick up where it stopped. They paid for those tokens, so don't throw them away. Interrupts work the same way: they come back as a value.

Streams always look like `.stream` plus `.response`, whether they come from generate, a flow, a tool or a prompt.

Auth and secrets ride on `context=`. Nested calls inherit it, traces redact it, and it never gets saved anywhere. Over HTTP, the only error text that leaves the server is a `PublicError` the author raised on purpose.

## Judgment calls

Use the same name for the same idea everywhere. It's `config=` on every call. If two calls disagree, someone will guess wrong.

Calling something directly should behave like Genkit calling it. `await my_tool(x)` returns and fails exactly the way it would inside `generate`, so tests mean something.

Two ways to do one thing is fine only if they end up as the same thing: a dict or a typed config, a model name string or a ref. Otherwise pick one. Be suspicious of your own convenience features: "accepts one or a list", a helper that just builds a string, the same type importable from two places. They rarely earn their keep.

What one call returns should go straight into the call that uses it. If `get_active_tools()` exists so people can pass the result to `generate(tools=...)`, it returns `list[Tool]`, not some internal type that fails validation.

One input shape per idea. If the constructor accepts a config entry, the method that adds one later accepts the same entry.

For a closed set of values the user passes in, use a `Literal`: `thinking_level='high'`. It autocompletes, reads as a plain string, and needs no import. Use an enum when the main thing people do with the value is compare against it, which usually means something Genkit hands back: `response.finish_reason == FinishReason.FAILED`, `failure.reason == ErrorReason.TOOL_FAILED`, `ScoreStatus.PASS`. Make it a `StrEnum` so comparing against the plain string still works. If the set keeps growing, like model ids, type it as `KnownGeminiModel | str`: users get autocomplete, and a new id works the day it ships.

Keep what the model sees separate from what the developer sees. Partial stream chunks don't go into history. A tool's return value isn't the same object as the tool-response wrapper the model reads.

Keep state as plain data. History, `Operation`, anything a user might store: it should round-trip through JSON.

The call that causes a problem should be the one that reports it. If `connect('git', command='uvxx-typo')` succeeds and the failure only shows up three calls later inside `generate`, the user is debugging the wrong line.

Tell "broken" apart from "down right now". A typo, a protocol error or a name collision should fail loudly. A server that's unreachable or timed out can be skipped and logged so the rest keeps working. Either way, raise a `GenkitError` with a status the caller can branch on.

An error should name the user's thing and say how to fix it: "server 'linear' isn't a stdio entry", not "2 validation errors" or an interpreter path. It should never echo the value back, because the value might be someone's key.

One rule, one message. If two places check the same thing, have them call the same check, so the user never sees two different errors for one mistake.

For overrides: leaving an argument out keeps the default, `[]` clears it, a list replaces it, and config merges key by key. Before adding a new one, ask who else reads or changes that value after your code runs. Middleware can rewrite the request after your check. Retry and Fallback act on whatever status you pick. Config merges across the ref, the prompt and the call. This is the question most designs miss.

Pick the safe default. Prompt and reply text stay off spans unless someone asks for them, and an explicit setting beats an environment variable. Don't make people pay for things they don't call; prompts load lazily for that reason.

Only export what someone outside the SDK would actually type. You can always add it later; removing it breaks people.

Put behavior on the class it belongs to instead of exporting a loose function. If the user already holds the object, it's a method: `paused.restart(...)`, `stream.to_sse()`. If they're building one, it's a classmethod or the constructor: `GoogleAI.gemini(...)`, `Part.from_text(...)`, `MultipartToolResponse(...)`. That way autocomplete on the thing they have shows them what they can do. A standalone function is fine when there's no object to hang it on, like the `genkit.web` helpers for people writing their own server adapter.

When you explain a choice, in a comment, a docstring or a PR, explain it by what the user experiences. "JS does it this way" is useful research, but it isn't a reason.

## Pydantic, dataclass, or plain class

Ask what the object is for.

If it's ever going to be JSON, it's Pydantic. The base class depends on who owns the keys:

- The app's own data (flow and tool input and output, or config for middleware the app wrote itself) is a plain `BaseModel`. Those are the user's keys, and we don't rename them.
- Settings the user hands to Genkit are a `GenkitConfig` (from `genkit.plugin_api`). That covers model config through `ModelConfig`, plugin and shared middleware config, and whatever's nested inside them. You construct it with `snake_case` arguments that all three type checkers accept. Its JSON is `camelCase`, because the Dev UI form, traces and `.prompt` files all have to agree on one spelling. Unknown keys raise, and so does passing both spellings of one setting. `model_dump()` is plain Pydantic, so provider SDKs get field names; pass `by_alias=True` when you want Genkit JSON. Don't hand-write `alias=` when it would just be `to_camel(name)`.
- `GenkitModel` is internal, for Genkit's own wire types (`Part`, `Message`, `ModelRequest`, spans). It dumps `camelCase` by default, which isn't what provider SDKs or user code expect, so never make it the base of anything a user or plugin author subclasses.

If it's only in-process data, like a handle or a context object passed around (`ModelRef`, `SpanMetadata`, `TurnContext`), use a frozen, keyword-only dataclass. Frozen means nothing downstream can quietly change it.

If it does things or has a lifecycle (`Genkit`, `Tool`, `Prompt`, `StreamResponse`, `Plugin`, `Middleware`), it's a plain class with private state and methods. Don't make it a Pydantic model just to get a free constructor: every internal field becomes public.

## Generated wire types

`genkit/_core/_typing.py` is generated from the schema shared by all the SDKs (`genkit-tools/genkit-schema.json`) by `py/scripts/schema_to_typing.py`. Don't edit it by hand; the next regeneration will undo your change.

If a type needs to look different in Python, change the generator's tables:

- `TRANSFORMATIONS` renames a type (`Error` becomes `OperationError` so it doesn't shadow the builtin), drops a field (`apiKey` from config, because config shows up in traces), or adds a suffix so a hand-written subclass can extend it.
- `FIELD_TYPE_OVERRIDES` tightens the type of one field.
- `EXCLUDED` is for types we write by hand.

Give each entry a one-line comment explaining why, in terms a user would care about. Then regenerate the file and run `generate_schema_typing --ci` to check it's in sync.

## Working alongside other agents

Assume you're not alone on this machine. Other agents may be editing their own copies of the repo and running their own Dev UIs at the same time, and nothing stops you from quietly debugging one of theirs.

Work in your own git worktree, created off the branch you were asked to change, and run everything from inside it. Use that worktree's environment (`uv run` from inside the worktree), not a shared one, or you'll be testing whatever another checkout installed.

When you use `genkit start`, make sure the Dev UI you're looking at is talking to your app:

- Start it from your worktree's project directory. The Dev UI only sees apps that registered under the directory it was started from (`.genkit/runtimes`), so separate worktrees get separate Dev UIs. Within one directory it can see several apps at once, each with its own runtime ID, and anything that doesn't name a runtime goes to the one started most recently. If a second app starts in your directory, your runs quietly go to it.
- Let it pick free ports, and read them from its output. Don't assume 4000 for the UI or 3100 for reflection. If you pin a port with `-p` or `GENKIT_REFLECTION_PORT`, expect it might be taken; a busy reflection port makes `Genkit()` fail at startup.
- Don't carry over `GENKIT_*` variables from another shell. A leftover `GENKIT_TELEMETRY_SERVER` sends your traces to another agent's Dev UI, and yours stays empty while things look like they're working.
- Before trusting a result, check you're in the right place: the flow you just added is in the list, and the trace you just ran shows up. If either is missing, you're connected to the wrong app.

Clean up only what you started. Stop your own process by its PID. Never run `pkill genkit`, kill whatever's on a port, or clear `.genkit/` in a directory you didn't create; that's someone else's session.

## PR descriptions

Reviewers mostly care about one thing: what this does to the public API. Write the description so they can judge that without reading the diff.

The title says what the user sees, in present tense, subject first: `fix(py)!: a failed agent turn returns res.error`. Add `!` when it breaks someone. Leave out the implementation; "refactor X internals" says nothing to a reviewer.

Open with one or two sentences: what a caller can do now, or what no longer breaks. Then a short snippet showing the call a user would write and what comes back, with `# before` / `# after` if the behavior changed. Include the exact error text if that's what changed.

### Changes

One bullet per change a user could notice, biggest first: a new or removed name, a new argument, a different return value, a new error, a different default. Say what it is now and why it belongs on the surface, in terms of what the user gets. Leave out internal moves and renames nobody imports. If a bullet needs more than two or three sentences, it's probably two changes.

### Breaking changes

List every change to the API surface that could break existing code: removed or renamed names, moved imports, arguments that became required or keyword-only, different return types, new errors where there used to be none. For each one, show what the old code does now and what to write instead:

```python
# before
from genkit_vertexai.model_garden import ModelGarden
# after
from genkit_vertexai import ModelGarden
```

If nothing breaks, say "None." so reviewers know you checked.

### Cross-SDK

Some of what Python writes is read by the other SDKs and by the tooling, so a change there isn't Python-only. That includes:

- the shared schema (`genkit-tools/genkit-schema.json`) and anything generated from it
- trace and span attributes the Dev UI reads
- the reflection API
- the HTTP flow format (`{"data": ...}`, `{"result": ...}`, SSE frames)
- `.prompt` frontmatter
- config keys as they show up in traces and the Dev UI form
- status names, finish reasons, and action kinds and metadata

If your PR changes any of these, add this section. Say what changed on the wire, show one example of the JSON before and after, and say what the JS, Go and Dart owners need to do: nothing, update a schema, handle a new field, or stop sending an old one. If Python now writes something the others don't yet read, or reads something they don't write, say so plainly so it doesn't get found in a broken trace.

If nothing on the wire changed, leave the section out. A Python-only rename doesn't belong here, as long as the JSON stays the same.

### Open question and verification

Put anything you haven't decided under `## Open question` with the options, so nobody approves a choice nobody made. Finish with what you actually ran to check it.

Leave out the story of how you got here, review-thread history, and "matches JS" as a reason. Describe the end state and why it's right for the user.
