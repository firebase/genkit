# API Stability Channels

As of version 1.0, Genkit is considered **Generally Available (GA)** and ready
for production use. Genkit follows [semantic versioning](https://semver.org/)
with breaking changes to the stable API happening only on major version
releases.

To gather feedback on potential new APIs and bring new features out quickly,
Genkit offers a **Beta** entrypoint that includes APIs that have not yet
been declared stable. The beta channel may include breaking changes on
*minor* version releases.

## Using the Stable Channel

To use the stable channel of Genkit, import from the standard
`"genkit"` entrypoint:

```ts
import { genkit, z } from "genkit";

const ai = genkit({plugins: [...]});
console.log(ai.apiStability); // "stable"
```

When you are using the stable channel, we recommend using the standard `^X.Y.Z`
dependency string in your `package.json`. This is the default that is used when
you run `npm install genkit`.

## Using the Beta Channel

To use the beta channel of Genkit, import from the `"genkit/beta"` entrypoint:

```ts
import { genkit, z } from "genkit/beta";

const ai = genkit({plugins: [...]});
console.log(ai.apiStability); // "beta"

// now beta features are available
```

When you are using the beta channel, we recommend using the `~X.Y.Z` dependency
string in your `package.json`. The `~` will allow new patch versions but will
not automatically upgrade to new minor versions which may have breaking changes
for beta features. You can modify your existing dependency string by changing
`^` to `~` if you begin using beta features of Genkit.

### Current Features in Beta

- **[Chat/Sessions](chat):** a first-class conversational `ai.chat()` feature
  along with persistent sessions that store both conversation history and an
  arbitrary state object.
- **[Interrupts](interrupts):** special tools that can pause generation for
  human-in-the-loop feedback, out-of-band processing, and more.
