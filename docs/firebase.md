
# Genkit with Firebase 🔥

1. Install required tools

    1. Make sure you are using node version 18 or higher (run `node --version` to check).

    1. Install [firebase CLI](https://firebase.google.com/docs/cli) and [gcloud cli](https://cloud.google.com/sdk/docs/install)

1. Login to Firebase

   ```
   firebase login
   # or if necessary
   firebase login --reauth

   # if running in cloud shell
   firebase login --no-localhost 
   ```

1. Create a new Firebase project via the [Firebase console](https://console.firebase.google.com/) or select an existing one. Make sure the project is on Blaze plan (i.e. has billing account).

1. After you have created / picked one, run the following to set an env var with your project ID and set the project as your default:

    ```
    export GCLOUD_PROJECT=<your-cloud-project>
    ```

1. Create a new folder for the project

   ```
   export GENKIT_PROJECT_HOME=~/tmp/genkit-firebase-project1
   mkdir -p $GENKIT_PROJECT_HOME
   cd $GENKIT_PROJECT_HOME
   ```

1. Initialize firebase project in the folder

    ```
    firebase init functions --project $GCLOUD_PROJECT
    ```

    For functions language pick _TypeScript_.

    Up to you whether you want ESLint, but for prototyping it might be getting in the way, recommend selecting "n".

    Feel free to say yes to installing dependencies with npm.

1. The sample uses the Google Generative AI API. You will need an API key from AI Studio, you can get one here: https://aistudio.google.com/app/apikey

    ```
    export GOOGLE_API_KEY=xyzYourKeyHere
    ```

1. Create a `functions/.env` file and add `GOOGLE_API_KEY=xyzYourKeyHere`.

1. Edit the `functions/tsconfig.json` file, and add the following option to the `compilerOptions`: 

    * `"skipLibCheck": true,`
    * also consider setting: `"noUnusedLocals": false`

    Your `tsconfig.json` file should look like this:
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

1. Install the Genkit packages. This step assumes you have access to the Genkit package tgz files and have them in the folder represented by `GENKIT_DIST` variable.

    ```
    cd functions
    mkdir genkit-dist
    cp $GENKIT_DIST/* genkit-dist
    npm i --save ./genkit-dist/*.tgz
    ```

1. Paste the following sample code into `functions/src/index.ts` file:
     ```javascript
     import { generate } from '@google-genkit/ai/generate';
     import { getProjectId } from '@google-genkit/common';
     import { configureGenkit } from '@google-genkit/common/config';
     import { run } from '@google-genkit/flow';
     import { generate } from '@google-genkit/ai/generate';
     import { firebase } from '@google-genkit/plugin-firebase';
     import { onFlow } from '@google-genkit/plugin-firebase/functions';
     import { geminiPro, googleGenAI } from '@google-genkit/plugin-google-genai';
     import * as z from 'zod';
     
     configureGenkit({
       plugins: [firebase({ projectId: getProjectId() }), googleGenAI()],
       flowStateStore: 'firebase',
       traceStore: 'firebase',
       enableTracingAndMetrics: true,
       logLevel: 'debug',
     });
     
     export const jokeFlow = onFlow(
       { name: 'jokeFlow', input: z.string(), output: z.string() },
       async (subject) => {
         const prompt = `Tell me a joke about ${subject}`;
        
         return await run('call-llm', async () => {
           const llmResponse = await generate({
             model: geminiPro,
             prompt: prompt,
           });
        
           return llmResponse.text();
         });
       }
     );
     ```

2. Build your code by running: 
    
    ```
    npm run build
    ```

3. Run your code locally: 

    ```
    npx genkit flow:run jokeFlow "\"banana\""
    ```

    Run Genkit Dev UI and try running the flow and explore traces:

    ```
    npx genkit start
    ```

    Open http://localhost:4000 in a browser.

4. Check that the _Default compute service account_ has the necessary permissions to run your Genkit flow. By default it usually has an _Editor_ role, but it's dependent on the organisation policy.

    Navigate to https://console.cloud.google.com/iam-admin/iam (make sure your project is selected) and search for the principal ending with `-compute@developer.gserviceaccount.com`

    At the very least it will need the following roles: _Cloud Datastore User_, _Vertex AI User_, _Logs Writer_, _Monitoring Metric Writer_, _Cloud Trace Agent_.

    If you don't see it on the list then you'll need to manually grant it (`YOUT_PROJECT_NUMBER-compute@developer.gserviceaccount.com`) the necessary permissions.

5. Run: 

    ```
    firebase deploy
    ```

6. Run the flow via the REST API.

    You can run the flow synchronously (blocking):

    ```
    curl -m 70 -X POST https://us-central1-$GCLOUD_PROJECT.cloudfunctions.net/jokeFlow -H "Authorization: bearer $(gcloud auth print-identity-token)" -H "Content-Type: application/json" -d '{"start": {"input": "banana"}}'
    ```

    You should see something like this:
    
    ```
    {"name":"bc042edd-efc4-48e9-8e36-23e4797e7a11","done":true,"result":{"response":"What did one banana say to the other?\n\nWe're about to split!"}}
    ```
