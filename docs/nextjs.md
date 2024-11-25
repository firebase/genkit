# Use Genkit in a Next.js app 

This page shows how you can use Genkit flows as server actions in your Next.js
apps.

## Before you begin

You should be familiar with Genkit's concept of [flows](flows), and how to write
them.

## Create a Next.js project

If you don't already have a Next.js project that you want to add generative AI
features to, you can create one for the purpose of following along with this
page:

```posix-terminal
npx create-next-app@latest
```

## Install Genkit dependencies

Install the Genkit dependencies into your Next.js app, the same way you would
for any Genkit project:

1.  Install the core Genkit library:

    ```posix-terminal
    npm i --save genkit
    ```

1.  Install at least one model plugin.

    For example, to use Google AI:

    ```posix-terminal
    npm i --save @genkit-ai/googleai
    ```

    Or to use Vertex AI:

    ```posix-terminal
    npm i --save @genkit-ai/vertexai
    ```

1.  If you didn't install the Genkit CLI globally, you can install it as a
    development dependency. The tsx tool is also recommended, as it makes
    testing your code more convenient. Both of these dependencies are optional,
    however.

    ```posix-terminal
    npm i --save-dev genkit-cli tsx
    ```

## Define Genkit flows

Create a new file in your Next.js project to contain your Genkit flows: for
example, `src/app/genkit.ts`. This file can contain your flows without
modification; however, because you can only run flows from a server backend, you
must add the `'use server'` directive to the top of the file.

For example:

```ts
'use server';

import { gemini15Flash, googleAI } from "@genkit-ai/googleai";
import { genkit, z } from "genkit";

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

export const menuSuggestionFlow = ai.defineFlow(
  {
    name: "menuSuggestionFlow",
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (restaurantTheme) => {
    const { text } = await ai.generate({
      model: gemini15Flash,
      prompt: `Invent a menu item for a ${restaurantTheme} themed restaurant.`,
    });
    return text;
  }
);
```

## Call your flows 

Now, in your frontend code, you can import your flows and call them as server
actions.

For example:

```tsx
'use client';

import { menuSuggestionFlow } from './genkit';
import { useState } from 'react';

export default function Home() {
  const [menuItem, setMenuItem] = useState<string>('');

  async function getMenuItem(formData: FormData) {
    const theme = formData.get('theme')?.toString() ?? '';
    const suggestion = await menuSuggestionFlow(theme);
    setMenuItem(suggestion);
  }

  return (
    <main>
      <form action={getMenuItem}>
        <label htmlFor="theme">
          Suggest a menu item for a restaurant with this theme:{' '}
        </label>
        <input type="text" name="theme" id="theme" />
        <br />
        <br />
        <button type="submit">Generate</button>
      </form>
      <br />
      <pre>{menuItem}</pre>
    </main>
  );
}
```

## Test your app locally

If you want to run your app locally, you need to make credentials for the model
API service you chose available.

- {Gemini (Google AI)}

  1.  Make sure Google AI is
      [available in your region](https://ai.google.dev/available_regions).

  1.  [Generate an API key](https://aistudio.google.com/app/apikey) for the
      Gemini API using Google AI Studio.

  1.  Set the `GOOGLE_GENAI_API_KEY` environment variable to your key:

      ```posix-terminal
      export GOOGLE_GENAI_API_KEY=<your API key>
      ```

- {Gemini (Vertex AI)}

  1.  In the Cloud console,
      [Enable the Vertex AI API](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=_)
      for your project.

  1.  Set some environment variables and use the
      [`gcloud`](https://cloud.google.com/sdk/gcloud) tool to set up application
      default credentials:

      ```posix-terminal
      export GCLOUD_PROJECT=<your project ID>

      export GCLOUD_LOCATION=us-central1

      gcloud auth application-default login
      ```

Then, run your app locally as normal:

```posix-terminal
npm run dev
```

All of Genkit's development tools continue to work as normal. For example, to
load your flows in the developer UI:

```posix-terminal
npx genkit start -- npx tsx --watch src/app/genkit.ts
```

## Deploy your app 

When you deploy your app, you will need to make sure the credentials for any
external services you use (such as your chosen model API service) are available
to the deployed app. See the following pages for information specific to your
chosen deployment platform:

- [Cloud Functions for Firebase](firebase)
- [Cloud Run](cloud-run)
- [Other Node.js platforms](deploy-node)
