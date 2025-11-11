# Anthropic Plugin Sample

This test app demonstrates minimal usage of the Genkit Anthropic plugin against both the stable and beta runners.

## Setup

1. From the repo root run `pnpm install` followed by `pnpm run setup` to link workspace dependencies.
2. In this directory, optionally run `pnpm install` if you want a local `node_modules/`.
3. Export an Anthropic API key (or add it to a `.env` file) before running any samples:

   ```bash
   export ANTHROPIC_API_KEY=your-key
   ```

## Available scripts

- `pnpm run build` – Compile the TypeScript sources into `lib/`.
- `pnpm run start:stable` – Run the compiled stable sample.
- `pnpm run start:beta` – Run the compiled beta sample.
- `pnpm run dev:stable` – Start the Genkit Dev UI over `src/stable.ts` with live reload.
- `pnpm run dev:beta` – Start the Genkit Dev UI over `src/beta.ts` with live reload.

Each source file defines a couple of flows that can be invoked from the Dev UI or the Genkit CLI (for example, `genkit flow:run anthropic-stable-hello`).
