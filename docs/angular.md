# Use Genkit in an Angular app

This page shows how you can use Genkit flows in Angular apps.

## Before you begin

You should be familiar with Genkit's concept of [flows](flows), and how to write
them.

## Create an Angular project

This guide will use an Angular app with
[SSR with server routing](https://angular.dev/guide/hybrid-rendering).

You can create a new project with server-side routing with the
[Angular CLI](https://angular.dev/installation#install-angular-cli):

```posix-terminal
ng new --ssr --server-routing
```

You can also add server-side routing to an existing project with the `ng add` command:

```posix-terminal
ng add @angular/ssr --server-routing
```

## Install Genkit dependencies

Install the Genkit dependencies into your Angular app, the same way you would
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

1.  Install the Genkit Express library:

    ```posix-terminal
    npm i --save @genkit-ai/express
    ```

1.  Install Zod:

    ```posix-terminal
    npm i --save zod
    ```

1.  If you didn't install the Genkit CLI globally, you can install it as a
    development dependency. The tsx tool is also recommended, as it makes
    testing your code more convenient. Both of these dependencies are optional,
    however.

    ```posix-terminal
    npm i --save-dev genkit-cli tsx
    ```

## Define Genkit flows

Create a new file in your Angular project to contain your Genkit flows: for
example, `src/genkit.ts`. This file can contain your flows without
modification.

For example:

```ts
import { gemini20Flash, googleAI } from "@genkit-ai/googleai";
import { genkit } from "genkit";
import { z } from "zod";

const ai = genkit({
  plugins: [googleAI()],
  model: gemini20Flash,
});

export const menuSuggestionFlow = ai.defineFlow(
  {
    name: "menuSuggestionFlow",
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (restaurantTheme) => {
    const { text } = await ai.generate(`Invent a menu item for a ${restaurantTheme} themed restaurant.`);
    return text;
  }
);
```

## Add server routes

Add the following imports to `src/server.ts`:

```ts
import { expressHandler } from '@genkit-ai/express';
import { menuSuggestionFlow } from './genkit';
```

Add the following line following your `app` variable initialization:

```ts
app.use(express.json());
```

Then, add a route to serve your flow:

```ts
app.post('/menu', expressHandler(menuSuggestionFlow));
```

## Call your flows

Now, you can run your flows from your client application.

For example, you can replace the contents of
`src/app/app.component.ts` with the following:

```ts
import { Component, resource, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { runFlow } from 'genkit/beta/client';

@Component({
  selector: 'app-root',
  imports: [FormsModule],
  templateUrl: './app.component.html',
})
export class AppComponent {
  menuInput = '';
  theme = signal('');

  menuResource = resource({
    request: () => this.theme(),
    loader: ({request}) => runFlow({ url: 'menu', input: request })
  });
}
```

Make corresponding updates to `src/app/app.component.html`:

```ts
<h3>Generate a custom menu item</h3>
<input type="text" [(ngModel)]="menuInput" />
<button (click)="this.theme.set(menuInput)">Generate</button>
<br />
@if (menuResource.isLoading()) {
  Loading...
} @else {
  <pre>{{menuResource.value()}}</pre>
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

  1.  Set the `GEMINI_API_KEY` environment variable to your key:

      ```posix-terminal
      export GEMINI_API_KEY=<your API key>
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
ng serve
```

All of Genkit's development tools continue to work as normal. For example, to
load your flows in the developer UI:

```posix-terminal
npx genkit start -- ng serve
```

## Deploy your app 

When you deploy your app, you will need to make sure the credentials for any
external services you use (such as your chosen model API service) are available
to the deployed app. See the following pages for information specific to your
chosen deployment platform:

- [Cloud Functions for Firebase](firebase)
- [Cloud Run](cloud-run)
- [Other Node.js platforms](deploy-node)
