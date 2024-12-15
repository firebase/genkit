# A Vertex AI plugin for Genkit

## Installing the plugin

```bash
npm i --save @genkit-ai/vertexai
```

## Using the plugin

```ts
import { genkit } from 'genkit';
import { vertexAI, gemini, gemini15Flash } from '@genkit-ai/vertexai';

const ai = genkit({
  plugins: [vertexAI()],
  model: gemini15Flash,
});

async () => {
  const { text } = ai.generate('hi Gemini!');
  console.log(text);
};
```

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [Genkit documentation](https://firebase.google.com/docs/genkit).

License: Apache 2.0
