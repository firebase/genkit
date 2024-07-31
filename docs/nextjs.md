# Firebase Genkit in Next.js apps

You can use Firebase Genkit flows as server actions in your Next.js apps.
The rest of this page shows you how.

## Requirements

Node.js 20 or later.

## Procedure

1.  Install the Genkit CLI by running the following command:

    ```posix-terminal
    npm i -g genkit
    ```

1.  If you don't already have a Next.js app you want to use, create one:

    ```posix-terminal
    npx create-next-app@latest
    ```

    Select TypeScript as your language of choice.

1.  Initialize Genkit in your Next.js project:

    ```posix-terminal
    cd your-nextjs-project

    genkit init
    ```

    - Confirm _yes_ when prompted whether to automatically configure Genkit for Next.js.
    - Select the model provider you want to use.

    Accept the defaults for the remaining prompts. The `genkit` tool will create
    some sample source files to get you started developing your own AI flows.

1.  Make API credentials available to your deployed function. Do one of the
    following, depending on the model provider you chose:

    - {Gemini (Google AI)}

      1.  Make sure Google AI is
          [available in your region](https://ai.google.dev/available_regions).

      1.  [Generate an API key](https://aistudio.google.com/app/apikey) for the
          Gemini API using Google AI Studio.

      1.  To run your flow locally, as in the next
          step, set the `GOOGLE_GENAI_API_KEY` environment variable to your key:

          ```posix-terminal
          export GOOGLE_GENAI_API_KEY=<your API key>
          ```

          When you deploy your app, you will need to make this key available in
          the deployed environment; exact steps depend on the platform.

    - {Gemini (Vertex AI)}

      1.  In the Cloud console,
          [Enable the Vertex AI API](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=_)
          for your project.

      1.  To run your flow locally, as in the next
          step, set some additional environment variables and use the
          [`gcloud`](https://cloud.google.com/sdk/gcloud) tool to set up
          application default credentials:

          ```posix-terminal
          export GCLOUD_PROJECT=<your project ID>

          export GCLOUD_LOCATION=us-central1

          gcloud auth application-default login
          ```

      1.  When you deploy your app, you will need to do the following:

          1.  Set the `GCLOUD_PROJECT` and `GCLOUD_LOCATION` variables in the
              deployed environment; exact steps depend on the platform.

          1.  If you're not deploying to a Firebase or Google Cloud environment,
              set up authorization for the Vertex AI API, using either
              [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
              (recommended) or a [service account key](https://cloud.google.com/iam/docs/service-account-creds#key-types).

          1.  On the [IAM](https://console.cloud.google.com/iam-admin/iam?project=_)
              page of the Google Cloud console, grant the **Vertex AI User**
              role (`roles/aiplatform.user`) to the identity you use to call the
              Vertex AI API.

              - On Cloud Functions and Cloud Run, this is the
                **Default compute service account**.
              - On Firebase App Hosting, it's your app's
                [backend service account](https://firebase.google.com/docs/app-hosting/about-app-hosting#service-account).
              - On other platforms, it's the identity you set up in the previous
                step.

    The only secret you need to set up for this tutorial is for the model
    provider, but in general, you must do something similar for each service
    your flow uses.

1.  If you allowed the `genkit init` command to generate a sample flow, it
    created a file, `genkit.ts`, that has a Genkit flow you can use as a server
    action. Try it out:

    1.  First, make a small change to tbe `callMenuSuggestionFlow` function:

        ```ts
        export async function callMenuSuggestionFlow(theme: string) {
          const flowResponse = await runFlow(menuSuggestionFlow, theme);
          console.log(flowResponse);
          return flowResponse;
        }
        ```

    1.  You can access this function as a server action. As a simple example,
        replace the contents of `page.tsx` with the following:

        ```tsx
        'use client';

        import { callMenuSuggestionFlow } from '@/app/genkit';
        import { useState } from 'react';

        export default function Home() {
          const [menuItem, setMenu] = useState<string>('');

          async function getMenuItem(formData: FormData) {
            const theme = formData.get('theme')?.toString() ?? '';
            const suggestion = await callMenuSuggestionFlow(theme);
            setMenu(suggestion);
          }

          return (
            <main>
              <form action={getMenuItem}>
                <label>
                  Suggest a menu item for a restaurant with this theme:{' '}
                </label>
                <input type="text" name="theme" />
                <button type="submit">Generate</button>
              </form>
              <br />
              <pre>{menuItem}</pre>
            </main>
          );
        }
        ```

    1.  Run it in the Next.js development environment:

        ```posix-terminal
        npm run dev
        ```

1.  You can also run and explore your flows in the Genkit Developer UI:

    ```posix-terminal
    genkit start
    ```
