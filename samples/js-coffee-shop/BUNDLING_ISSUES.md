# Genkit JS: Bundle Size Issues for Edge/Sandboxed Runtimes

When bundling Genkit for deployment to edge runtimes like Cloudflare Workers (via [Dynamic Worker Loaders](https://developers.cloudflare.com/workers/runtime-apis/bindings/worker-loader/)), the resulting bundle is significantly larger than necessary. This is because `@genkit-ai/core` unconditionally imports heavy server-side dependencies at the module level, even when those code paths are disabled at runtime via `sandboxedRuntime: true` and `jsonSchemaMode: 'interpret'`.

---

## Why some setups need stubs and others don’t (Workers “code generation” error)

Cloudflare Workers disallow **code generation from strings** (`eval`, `new Function`). Whether you hit that depends on **which code paths run at runtime**, not just what’s in the bundle.

| Dependency   | Uses `new Function` when …                         | Needed in Worker loader bundle? |
|-------------|-----------------------------------------------------|----------------------------------|
| **Handlebars** (via dotprompt) | Compiling a prompt template (`Handlebars.compile()`) | **Yes, if you use `definePrompt()`** — stub required. |
| **ajv**     | Validating with compiled schema (`ajv.compile(schema)`) | **No** when `jsonSchemaMode: 'interpret'` is set before flows run — that path is never taken. |
| **jsonpath-plus** | Some path operations (e.g. internal use in google-genai) | **No** in typical flows — the path that uses code gen isn’t hit. |

- **Coffee-shop (Worker Loader bundle)** uses **`definePrompt()`** with Handlebars-style templates (`{{customerName}}`, etc.). At runtime, dotprompt calls **Handlebars.compile()**, which uses `new Function` → **EvalError** unless Handlebars is stubbed. So this setup **must** alias Handlebars to a stub that does simple `{{var}}` substitution without code gen. With `jsonSchemaMode: 'interpret'` set in `genkit-config.js` before flow imports, **ajv** and **jsonpath-plus** are never on the code path that runs code gen; stubbing them is **optional** (only for bundle size, not for correctness).

- **Example worker** (e.g. `genkit-workers-example`) uses **inline prompts** (template literals) and `ai.generate({ prompt, output: { schema } })` — it does **not** use `definePrompt()`. So dotprompt/Handlebars are never used to compile a template, and no Handlebars stub is needed. **`definePrompt()` is not supported** on Workers unless you use a Handlebars stub; the example marks it as unsupported and uses inline prompts instead.

**Summary:** The only **required** stub for the Worker Loader flows bundle (when using `definePrompt`) is **Handlebars**. Ajv and jsonpath-plus stubs were added out of caution but are **not required** for correctness when using interpret mode; they can be commented out to reduce complexity or re-enabled later if you want to trim bundle size.

## Issue 1: `ajv` is always imported, even when `jsonSchemaMode: 'interpret'` is set

### The problem

Genkit documents that sandboxed environments (like Cloudflare Workers) that restrict `eval()` should use the `interpret` schema validation mode, which uses `@cfworker/json-schema` instead of `ajv`:

```typescript
setGenkitRuntimeConfig({
  jsonSchemaMode: 'interpret',
  sandboxedRuntime: true,
});
```

However, in `@genkit-ai/core/src/schema.ts`, `ajv` is imported and **instantiated unconditionally** at the top level:

```typescript
// schema.ts — lines 18-27
import Ajv, { type ErrorObject, type JSONSchemaType } from 'ajv';
import addFormats from 'ajv-formats';
// ...
const ajv = new Ajv();
addFormats(ajv);
```

The runtime config check happens later, inside `validateSchema()`:

```typescript
// schema.ts — lines 135-151
const validationMode = getGenkitRuntimeConfig().jsonSchemaMode;

if (validationMode === 'interpret') {
  // uses @cfworker/json-schema — ajv is never touched
  // ...
}

// ajv path — only reached when mode is NOT 'interpret'
const validator = validators.get(toValidate) || ajv.compile(toValidate);
```

Because `import Ajv from 'ajv'` and `new Ajv()` execute at module load time — before any config is set — there is no way to avoid bundling `ajv` and `ajv-formats`. This adds ~6,000 lines (unminified) of dead code to the bundle, including transitive dependencies like `fast-uri`, `fast-deep-equal`, and `json-schema-traverse`.

### Suggested fixes

#### Option A: Pluggable validator via registration pattern (preferred)

A simple separate entry point won't work because `validateSchema` / `parseSchema` are called from deep inside genkit's own internals (`action.ts`, `tool.ts`, `response.ts`) — code paths that run in every environment. These internal callers can't conditionally import from different entry points.

Instead, the validator implementation could be made pluggable via a registration pattern:

```typescript
// schema.ts — no ajv or cfworker import at the top level
type SchemaValidatorFn = (data: unknown, schema: JSONSchema) => {
  valid: boolean;
  errors?: ValidationErrorDetail[];
};

let schemaValidator: SchemaValidatorFn | undefined;

export function registerSchemaValidator(validator: SchemaValidatorFn) {
  schemaValidator = validator;
}

export function validateSchema(data: unknown, options: ProvidedSchema) {
  if (!schemaValidator) {
    throw new GenkitError({
      status: 'FAILED_PRECONDITION',
      message: 'No schema validator registered. Call registerSchemaValidator() during init.',
    });
  }
  const schema = toJsonSchema(options);
  if (!schema) return { valid: true, schema };
  return { ...schemaValidator(data, schema), schema };
}
```

The registration would happen automatically inside `setGenkitRuntimeConfig()`, based on the `jsonSchemaMode` value the user already provides. No new user-facing API is needed:

```typescript
// config.ts
export function setGenkitRuntimeConfig(config: GenkitRuntimeConfig) {
  runtimeConfig = { ...runtimeConfig, ...config };

  if (config.jsonSchemaMode === 'interpret') {
    // Dynamic import — bundlers can exclude ajv entirely
    const { Validator } = require('@cfworker/json-schema');
    registerSchemaValidator((data, schema) => { /* cfworker-based */ });
  } else {
    // Default Node.js path
    const Ajv = require('ajv').default;
    const addFormats = require('ajv-formats').default;
    const ajv = new Ajv();
    addFormats(ajv);
    registerSchemaValidator((data, schema) => { /* ajv-based */ });
  }
}
```

For the edge case, a default validator (ajv) could be registered at module load time as a fallback, so everything works without calling `setGenkitRuntimeConfig()` at all — preserving backwards compatibility.

From the user's perspective, nothing changes. They already call:

```typescript
setGenkitRuntimeConfig({
  jsonSchemaMode: 'interpret',
  sandboxedRuntime: true,
});
```

The difference is that internally, this would now control *which validator is loaded*, not just which code path is taken at validation time. The `require()` calls are inside conditional branches, so a bundler configured with `ajv` as external won't fail at build time — the `require('ajv')` branch is only reachable when `jsonSchemaMode` is not `'interpret'`.

This keeps `validateSchema` synchronous, avoids any import of `ajv` in edge environments, and requires no changes to internal callers (`action.ts`, `tool.ts`, `response.ts`) or user code.

#### Why not dynamic `import()` or lazy `require()`?

- **Dynamic `import()`** would make `getAjv()` async, forcing `validateSchema()` to become async too — a breaking change for all internal callers (`action.ts`, `tool.ts`, `response.ts`) and external consumers.
- **Lazy `require()`** keeps the function synchronous, but bundlers still statically analyze `require()` calls and will either bundle the module or error when it's externalized (as happens with `target: "browser"` in Bun). It doesn't achieve the goal of excluding `ajv` from the bundle.

---

## Issue 2: Express, OpenTelemetry, and the Reflection Server are always bundled

### The problem

`@genkit-ai/core/src/index.ts` barrel-exports everything from `reflection.ts`:

```typescript
// index.ts — line 85
export * from './reflection.js';
```

`reflection.ts` unconditionally imports Express and its associated middleware at the top level:

```typescript
// reflection.ts — lines 17-19
import express from 'express';
import fs from 'fs/promises';
import getPort, { makeRange } from 'get-port';
```

The `ReflectionServer.start()` method does check `sandboxedRuntime` and early-returns:

```typescript
// reflection.ts — lines 132-137
async start() {
  if (getGenkitRuntimeConfig().sandboxedRuntime) {
    logger.debug(
      'Skipping ReflectionServer start: not supported in sandboxed runtime.'
    );
    return;
  }
  // ... starts Express server ...
}
```

But this is a **runtime** guard, not a **build-time** one. Because the `import express` statement is at the top of the file, and `index.ts` re-exports everything via `export *`, the entire Express dependency tree is pulled into any bundle that imports from `@genkit-ai/core`. This includes:

- `express` (~20k lines with body-parser, cookie, etc.)
- `cors`
- `get-port`

Similarly, `@genkit-ai/core/package.json` lists the full OpenTelemetry SDK as direct dependencies:

```json
{
  "dependencies": {
    "@opentelemetry/api": "^1.9.0",
    "@opentelemetry/context-async-hooks": "~1.25.0",
    "@opentelemetry/core": "~1.25.0",
    "@opentelemetry/exporter-jaeger": "^1.25.0",
    "@opentelemetry/sdk-metrics": "~1.25.0",
    "@opentelemetry/sdk-node": "^0.52.0",
    "@opentelemetry/sdk-trace-base": "~1.25.0",
    "express": "^4.21.0",
    "cors": "^2.8.5",
    "get-port": "^5.1.0"
  }
}
```

The OpenTelemetry SDK pulls in `@grpc/grpc-js`, `protobufjs`, `semver`, and various exporters (Jaeger, Zipkin, OTLP via gRPC/HTTP/proto), adding ~50k+ lines to the bundle.

None of this code executes in a sandboxed runtime, but it all gets bundled.

### Impact

A minimal Genkit app with a single flow and the Google AI plugin produces a **~7MB unminified bundle** when all packages are inlined. The actual application code is a few hundred lines. The breakdown:

| Dependency group | Approx. size | Used in sandboxed runtime? |
|---|---|---|
| `@opentelemetry/*` + `@grpc/grpc-js` + `protobufjs` | ~50k lines | No |
| `express` + middleware | ~20k lines | No |
| `ajv` + `ajv-formats` | ~6k lines | No (when `interpret` mode) |
| `handlebars` + `source-map` (via dotprompt) | ~8k lines | Possibly |
| `node-fetch` + polyfills | ~2k lines | No (Workers has native fetch) |
| Genkit core + AI + google-genai | Remainder | Yes |

### Suggested fixes

1. **Don't barrel-export `reflection.ts` from `index.ts`** — move it to a separate entry point (e.g. `@genkit-ai/core/reflection`) so it's only imported when explicitly needed. The `export * from './reflection.js'` on line 85 of `index.ts` is the single line responsible for pulling Express into every consumer's bundle.

2. **Make OpenTelemetry dependencies optional or lazy** — the telemetry provider could be loaded on-demand rather than as a top-level import. For sandboxed environments, telemetry is typically not needed.

3. **Consider splitting `@genkit-ai/core` into runtime vs. dev concerns** — a lightweight `@genkit-ai/core/runtime` entry point containing just flows, actions, schemas, and config would allow edge deployments to avoid the dev server and telemetry infrastructure entirely.

---

## Issue 3: OpenTelemetry is always wired, even when `sandboxedRuntime: true`

### The problem

When `sandboxedRuntime: true` is set, the Reflection server and dev UI are correctly skipped at runtime. Telemetry, however, is still **registered and used**: the SDK is initialised, `NodeSDK` and `BatchSpanProcessor` are constructed, and `trace.getTracer()` / `tracer.startActiveSpan()` etc. are called. In a sandboxed Worker there is no exporter or backend, so this is dead work and forces the bundle to depend on (or stub) the entire OpenTelemetry API surface.

**Env behaviour:** Genkit does **not** use `NODE_ENV` for any of this. It uses **`GENKIT_ENV`** (default `'prod'`) in `getCurrentEnv()` / `isDevEnv()`:

- **Reflection server** is gated on `isDevEnv()` (i.e. `GENKIT_ENV === 'dev'`), so in prod it is not started. The code is still imported and bundled.
- **OpenTelemetry** is not gated on `GENKIT_ENV` or `NODE_ENV` or `sandboxedRuntime`. It is only skipped if the app (or a plugin) explicitly calls the hidden `disableGenkitOTelInitialization()`. So in production, and in Workers with `sandboxedRuntime: true`, OTel is still used unless you disable it yourself.

So “prod” (or `NODE_ENV=production`) does **not** exclude or disable OpenTelemetry.

### Wider fix (upstream)

Telemetry should be **disabled when `sandboxedRuntime: true`** or when `getCurrentEnv() === 'prod'` (or both), so that:

- No `@opentelemetry/*` code runs at all.
- No need to bundle or stub OTel for Workers.

Concretely: wherever the OTel SDK is initialised or `getTracer()` is used, guard with `getGenkitRuntimeConfig().sandboxedRuntime` (or an explicit `telemetry: false`-style option) and skip registration / use a no-op tracer from the API that does nothing. That way edge bundles never hit OTel code paths.

### Current workaround (this repo)

The CLI uses a **no-op OpenTelemetry stub** for all `@opentelemetry/*` imports: a universal Proxy so any method (`startActiveSpan`, `startSpan`, `recordException`, etc.) is a function that either invokes a callback with a fake span or returns a fake span. This avoids “X is not a function” at runtime but is whack-a-mole and doesn’t address the fact that OTel shouldn’t run in prod/sandboxed at all.

---

## Current workaround (this repo: Worker Loader flows bundle)

- **Handlebars (required when using `definePrompt()`)**  
  Alias `handlebars` and `handlebars/dist/cjs/handlebars.js` to a stub (`app/handlebars-stub.js`) that implements `compile()` with simple `{{var}}` substitution and no `new Function`, so Workers’ “code generation from strings” restriction is not triggered.

- **ajv / ajv-formats / jsonpath-plus (optional)**  
  With `jsonSchemaMode: 'interpret'` set before flow imports, the code paths that call `ajv.compile()` or jsonpath’s code gen are not run, so **stubbing these is not required** for correctness. Stubs can be used if you want to reduce bundle size by avoiding bundling the real packages; otherwise they can be left commented out.

When bundling for Cloudflare Workers, these dependencies can be marked as `external` (or otherwise excluded) to keep the bundle size manageable:

```typescript
external: [
  // Node builtins (resolved by workerd's nodejs_compat)
  "child_process", "crypto", "dns", "events", "fs", "http", "http2",
  "https", "net", "os", "path", "stream", "tls", "url", "util",
  "zlib", "buffer", "querystring", "string_decoder", "worker_threads",
  "perf_hooks", "async_hooks", "dgram", "inspector", "node:module",
  // Server-side deps (dead code in sandboxed runtime)
  "express",
  "@grpc/grpc-js",
  "@opentelemetry/*",
  "node-fetch",
  "encoding",
  "source-map",
]
```

`ajv` and `ajv-formats` are still imported at module load time in `@genkit-ai/core`, so if not stubbed they remain in the bundle as dead weight when using interpret mode; they do not need to be stubbed to avoid runtime errors.
