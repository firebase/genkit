# Google Gemini Developer API plugin for Genkit

## Installing the plugin

```bash
npm i --save @genkit-ai/googleai
```

## Using the plugin

```ts
import { genkit } from 'genkit';
import { googleAI, gemini } from '@genkit-ai/googleai';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini('gemini-1.5-flash'),
});

async () => {
  const { text } = ai.generate('hi Gemini!');
  console.log(text);
};
```

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [Genkit documentation](https://genkit.dev/docs/plugins/google-genai/).

License: Apache 2.0
