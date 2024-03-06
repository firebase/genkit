# Genkit with Cloud Run

1. Install required tools
    1. make sure you are using node version 18 or higher (run `node --version` to check).
    1. install [gcloud cli](https://cloud.google.com/sdk/docs/install)

1. Create a directory for the Genkit sample project:

    ```
    export GENKIT_PROJECT_HOME=~/tmp/genkit-express-project1
    mkdir -p $GENKIT_PROJECT_HOME
    cd $GENKIT_PROJECT_HOME
    ```

    If you're going to use an IDE, open it to this directory.

1. Initialize the nodejs project:

    ```
    npm init -y
    ```

1. You will need a GCP or Firebase project for persisting traces in Firestore. After you have created / picked one, run the following to set an env var with your project ID and set the project as your default:

    ```
    export GCLOUD_PROJECT=<your-cloud-project>
    ```
    ```
    gcloud config set project $GCLOUD_PROJECT
    ```

    NOTE: Your project must have billing enabled.

1. You will need Application Default Credentials. Run:

    ```
    gcloud auth application-default login
    ```

1. Enable services used in this sample app:

     1. Enable Firestore by navigating to https://pantheon.corp.google.com/firestore/databases?project=_ and click "Create Database".

     1. Enable Vertex AI by running: 

        ```
        gcloud services enable aiplatform.googleapis.com
        ```

     1. Enable Compute Engine API (used for Cloud Functions)

        ```
        gcloud services enable compute.googleapis.com
        ```

1. Create tsconfig.json file (```touch tsconfig.json```) and paste this:
    ```
    {
       "compilerOptions": {
          "module": "commonjs",
         "noImplicitReturns": true,
         "noUnusedLocals": false,
         "outDir": "lib",
         "sourceMap": true,
          "strict": true,
         "target": "es2017",
         "skipLibCheck": true,
         "esModuleInterop": true
       },
        "compileOnSave": true,
       "include": [
         "src"
       ]
     }
     ```

    Replace the contents of your package.json file with the following:
     ```
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

1. Install Genkit packages. This steps assumes you have access to genkit package tgz files and have them in the folder represented by GENKIT_DIST variable.

    ```
    mkdir genkit-dist
    cp $GENKIT_DIST/*.tgz genkit-dist
    npm install --save-dev typescript
    npm i --save ./genkit-dist/*.tgz
    ```

1. Create the src/index.ts file where your Genkit code will live:

    ```
    mkdir src
    touch src/index.ts
    ```

    Paste the following sample code into src/index.ts file:
   
    ```javascript
    import { generate } from '@google-genkit/ai/generate';
    import { GenerationResponseChunkSchema } from '@google-genkit/ai/model';
    import { getLocation, getProjectId } from '@google-genkit/common';
    import { configureGenkit } from '@google-genkit/common/config';
    import { flow, run, startFlowsServer } from '@google-genkit/flow';
    import { firebase } from '@google-genkit/plugin-firebase';
    import { geminiPro, vertexAI } from '@google-genkit/plugin-vertex-ai';
    import * as z from 'zod';
    
    configureGenkit({
      plugins: [
        firebase({ projectId: getProjectId() }),
        vertexAI({ projectId: getProjectId(), location: getLocation() || 'us-central1' }),
      ],
      flowStateStore: 'firebase',
      traceStore: 'firebase',
      enableTracingAndMetrics: true,
      logLevel: 'debug',
    });
    
    export const jokeFlow = flow(
      { name: 'jokeFlow', input: z.string(), output: z.string(), streamType: GenerationResponseChunkSchema },
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
    
    startFlowsServer()
    ```


1. Build and run your code:

   ```
   npm run build
   npx genkit flow:run jokeFlow "\"banana\"" -s
   ```

1. Start the dev UI:

    ```npx genkit start```

    1. To try out the joke flow navigate to http://localhost:4000/flows and run the flow via the Dev UI.

    1. Try out the express endpoint:
        ```
        curl -X POST http://127.0.0.1:5000/jokeFlow?stream=true -H "Content-Type: application/json"  -d '{"start": {"input": "banana"}}'
        ```

1. To deploy to Cloud Run first check that the "Default compute service account" has the necessary permissions to run your flow. By default it usually has an "Editor" role, but it's dependent on the org policy.

    Navigate to https://pantheon.corp.google.com/iam-admin/iam (make sure your project is selected) and search for the Principal ending with `-compute@developer.gserviceaccount.com`

    At the very least it will need the following roles: Cloud Datastore User, Vertex AI User, Logs Writer, Monitoring Metric Writer, Cloud Trace Agent.

    If you don't see it on the list then you'll need to manually grant it (`YOUT_PROJECT_NUMBER-compute@developer.gserviceaccount.com`) the necessary permissions.

    For reference: https://screencast.googleplex.com/cast/NTc2MDM0NjMzNjc4ODQ4MHw4ZWU2NDA2YS01Ng


1. Deploy to Cloud Run:

    ```
    gcloud run deploy --update-env-vars GCLOUD_PROJECT=$GCLOUD_PROJECT
    ```

    Test out your deployed app!

    ```
    export MY_CLOUD_RUN_SERVICE_URL=https://.....run.app
    ```
    ```
    curl -m 70 -X POST $MY_CLOUD_RUN_SERVICE_URL/jokeFlow?stream=true -H "Authorization: bearer $(gcloud auth print-identity-token)" -H "Content-Type: application/json"  -d '{"start": {"input": "banana"}}'
    ```


