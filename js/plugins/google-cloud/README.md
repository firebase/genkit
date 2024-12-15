# Google Cloud plugin for Genkit

## Installing the plugin

```bash
npm i --save @genkit-ai/google-cloud
```

## Using the plugin

```ts
import { genkit } from 'genkit';
import {
  enableGoogleCloudTelemetry,
} from '@genkit-ai/google-cloud';

enableGoogleCloudTelemetry();

const ai = genkit({
  plugins: [
    // ...
  ],
});
```

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [Genkit documentation](https://firebase.google.com/docs/genkit).

License: Apache 2.0
