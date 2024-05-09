Genkit CLI.

Right now this is just scaffolding. To build,

```
pnpm i
pnpm build
```

After executing `npm link`, the `genkit` binary will be in your local path.
Call `genkit example` to see the example.

We're following a slightly different architecture from Firebase Tools. For
commands, Firebase Tools relies on node `require()` calls to dynamically load
code. This is discouraged (in fact, disabled per our TSLint) so instead
all files (and thus all commands) need to be directly referenced from something
in the tree of imports. See `src/cli.ts`.
