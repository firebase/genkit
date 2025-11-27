# Firebase plugin for Genkit

See the official documentation for more:

- [Deploying Genkit with Firebase](https://genkit.dev/docs/deployment/firebase/)
- [Genkit monitoring with Firebase](https://genkit.dev/docs/observability/getting-started/)

## Installing the plugin

```bash
npm i --save @genkit-ai/firebase
```

## Using the plugin

```ts
import { genkit } from 'genkit';
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry();

const ai = genkit({
  plugins: [
    // ...
  ],
});
```

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [Genkit documentation](https://genkit.dev/).

License: Apache 2.0
