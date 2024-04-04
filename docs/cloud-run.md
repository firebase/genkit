# Genkit with Cloud Run

1.  Install required tools

    1.  make sure you are using node version 18 or higher (run `node --version`
        to check).
    1.  install [gcloud cli](https://cloud.google.com/sdk/docs/install)

1.  Create a directory for the Genkit sample project:

    ```posix-terminal
    export GENKIT_PROJECT_HOME=~/tmp/genkit-express-project1

    mkdir -p $GENKIT_PROJECT_HOME

    cd $GENKIT_PROJECT_HOME
    ```

    If you're going to use an IDE, open it to this directory.

1.  Initialize the nodejs project:

    ```posix-terminal
    npm init -y
    ```

1.  Initialize Genkit in your Firebase project:

    Download and unzip [genkit-dist.zip](https://bit.ly/genkit-dist) (e.g. `$HOME/Downloads/genkit-dist`).

    Start by installing Genkit CLI

    ```posix-terminal
    cd functions

    npm i --save -D $HOME/Downloads/genkit-dist/genkit-0.0.7.tgz $HOME/Downloads/genkit-dist/genkit-ai-tools-plugins-0.0.7.tgz
    ```

    Then run:

    ```posix-terminal
    npx genkit init -d $HOME/Downloads/genkit-dist/genkit-dist.zip
    ```

    Select `googleCloud` as the deployment platform option and Vertex AI as the model. Choose defaults for the rest of the options.

1.  You will need a Google Cloud or Firebase project for persisting traces in
    Firestore. After you have created / picked one, run the following to set an
    env var with your project ID and set the project as your default:

    ```posix-terminal
    export GCLOUD_PROJECT=<your-cloud-project>

    gcloud config set project $GCLOUD_PROJECT
    ```

    NOTE: Your project must have billing enabled.

1.  You will need Application Default Credentials. Run:

    ```posix-terminal
    gcloud auth application-default login
    ```

1.  Enable services used in this sample app:

    1.  Enable Firestore by navigating to
        https://console.cloud.google.com/firestore/databases?project=_ and click
        "Create Database".

    1.  Enable Vertex AI by running:

        ```posix-terminal
        gcloud services enable aiplatform.googleapis.com
        ```

    1.  Enable Compute Engine API (used for Cloud Functions)

        ```posix-terminal
        gcloud services enable compute.googleapis.com
        ```

1.  Replace the contents of your package.json file with the following:

    ```json
    {
      "name": "genkit-express-project1",
      "version": "1.0.0",
      "description": "",
      "main": "lib/index.js",
      "scripts": {
        "start": "node lib/index.js",
        "compile": "tsc",
        "build": "npm run build:clean && npm run compile",
        "build:clean": "rm -rf ./lib",
        "build:watch": "tsc --watch"
      },
      "keywords": [],
      "author": "",
      "license": "ISC",
      "devDependencies": {
        "typescript": "^5.3.3"
      },
      "dependencies": {
        "express": "^4.18.2"
      }
    }
    ```

1.  Paste the following sample code into src/index.ts file:

    ```javascript
    import { generate } from '@genkit-ai/ai';
    import { GenerateResponseChunkSchema } from '@genkit-ai/ai/model';
    import { configureGenkit } from '@genkit-ai/core';
    import { defineFlow, run, startFlowsServer } from '@genkit-ai/flow';
    import { firebase } from '@genkit-ai/firebase';
    import { geminiPro, vertexAI } from '@genkit-ai/vertexai';
    import * as z from 'zod';

    configureGenkit({
      plugins: [
        firebase(),
        vertexAI({
          location: 'us-central1',
        }),
      ],
      flowStateStore: 'firebase',
      traceStore: 'firebase',
      enableTracingAndMetrics: true,
      logLevel: 'debug',
    });

    export const jokeFlow = defineFlow(
      {
        name: 'jokeFlow',
        inputSchema: z.string(),
        outputSchema: z.string(),
        streamType: GenerateResponseChunkSchema,
      },
      async (subject, streamingCallback) => {
        return await run('call-llm', async () => {
          const llmResponse = await generate({
            prompt: `Tell me a long joke about ${subject}`,
            model: geminiPro,
            config: {
              temperature: 1,
            },
            streamingCallback,
          });

          return llmResponse.text();
        });
      }
    );

    startFlowsServer();
    ```

1.  Build and run your code:

    ```posix-terminal
    npm run build
    npx genkit flow:run jokeFlow "\"banana\"" -s
    ```

1.  Start the Developer UI:

    ```posix-terminal
    npx genkit start
    ```

    1.  To try out the joke flow navigate to http://localhost:4000/flows and run
        the flow using the Developer UI.

    1.  Try out the express endpoint:

        ```posix-terminal
        curl -X POST "http://127.0.0.1:3400/jokeFlow?stream=true" -H "Content-Type: application/json"  -d '{"data": "banana"}'
        ```

1.  To deploy to Cloud Run first check that the "Default compute service
    account" has the necessary permissions to run your flow. By default it
    usually has an "Editor" role, but it's dependent on the org policy.

    Navigate to https://console.cloud.google.com/iam-admin/iam (make sure your
    project is selected) and search for the Principal ending with
    `-compute@developer.gserviceaccount.com`

    At the very least it will need the following roles: Cloud Datastore User,
    Vertex AI User, Logs Writer, Monitoring Metric Writer, Cloud Trace Agent.

    If you don't see it on the list then you'll need to manually grant it
    (`YOUT_PROJECT_NUMBER-compute@developer.gserviceaccount.com`) the necessary
    permissions.

1.  Deploy to Cloud Run:

    ```posix-terminal
    gcloud run deploy --update-env-vars GCLOUD_PROJECT=$GCLOUD_PROJECT
    ```

    Test out your deployed app!

    ```posix-terminal
    export MY_CLOUD_RUN_SERVICE_URL=https://.....run.app

    curl -m 70 -X POST $MY_CLOUD_RUN_SERVICE_URL/jokeFlow?stream=true -H "Authorization: bearer $(gcloud auth print-identity-token)" -H "Content-Type: application/json"  -d '{"data": "banana"}'
    ```
