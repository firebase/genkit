# Typed Context

Demonstrates **typed context** in Genkit: define an `AppContext` type, pass it to `genkit<AppContext>({...})`, and get typed `context` in flows, tools, `generate()` options, and `ai.currentContext()`.

## What this sample shows

| Feature | Description |
|--------|-------------|
| **AppContext type** | Declare your app’s context shape (e.g. `echo`, `hello`, `userId`). |
| **genkit&lt;AppContext&gt;()** | Create the instance with the type so `context` is typed everywhere. |
| **Flows** | Flow callbacks receive `context: AppContext & ActionContext`. |
| **Tools** | Tool callbacks receive the same typed context. |
| **currentContext()** | `ai.currentContext()` returns `(AppContext & ActionContext) \| undefined`. |
| **Override at run time** | Pass a different `context` when calling a flow or action. |

If you call `genkit()` without the type argument, `context` in flows/tools is typed as `ActionContext` and properties like `context.hello` are `any`.

## Setup

From the repo root:

```bash
pnpm install
pnpm run setup
```

## Run the sample

From this directory:

```bash
pnpm build && pnpm start
```

Or run the source directly:

```bash
pnpm exec tsx src/index.ts
```

## Example output

```
Echo with default context: foo
Echo with overridden context: foo foo
Greet: Hello, World!
currentContext() without userId: test (user: anonymous)
currentContext() with userId: test (user: user-123)
Tool with typed context: Hello, Tool User!
```
