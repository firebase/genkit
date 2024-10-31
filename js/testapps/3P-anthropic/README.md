This test app is temporary and for doing e2e tests of the 3P plugins with `0.9`

To run this app:

1. obtain an anthropic API key, put it in a `.env` file in this apps directory as ANTHROPIC_API_KEY
2. make sure you've ran `pnpm i` and `pnpm run setup` in the root of this repo
3. in this app directory run `npm run build` and then `npm run genkit:dev`
4. in another terminal do `genkit flow:run jokeFlow \"chicken\"

(there is a bug on the dev ui right now, so we will test things via the CLI)

at the moment it will throw some telemetry errors about saving trace,
we can worry about those later (i think we just need to provide it with a telemetry server or something now)

Notice in the package.json that I've just installed a locally packed version of the plugin.

We can do this or provide a filepath as the dependency, or we can use `npm link`