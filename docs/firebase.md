
# Genkit with Firebase 🔥

1. Install required tools

    1. make sure you are using node version 18 or higher (run `node --version` to check).

    1. install [firebase CLI](https://firebase.google.com/docs/cli) and [gcloud cli](https://cloud.google.com/sdk/docs/install)

1. Login to firebase

   ```
   firebase login
   # or if necessary
   firebase login --reauth

   # if running in cloud shell
   firebase login --no-localhost 
   ```

1. Create a new Firebase project https://firebase.corp.google.com or select an existing one. Make sure the project is on Blaze plan (i.e. has billing account).

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

1. initialize firebase project in the folder

    ```
    firebase init functions --project $GCLOUD_PROJECT
    ```

    For functions language pick TypeScript
    Up to you whether you want ESLint, but for prototyping it might be getting in the way, recommend selecting "n".
    Feel free to say yes to installing dependencies with npm.

1. The sample is using Google Generative AI API. You will need an API Key from AI Studio: https://aistudio.google.com/app/apikey

    ```
    export GOOGLE_API_KEY=xyzYourKeyHere
    ```

1. Create `functions/.env` file and add `GOOGLE_API_KEY=xyzYourKeyHere` in there as well.

1. Edit `tsconfig.json` file -- add the following option to the compilerOptions: `"skipLibCheck": true,`

    also consider setting: `"noUnusedLocals": false`

    your tsconfig.json file should look like this:
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

1. Install Genkit packages:

    ```
    cd functions
    mkdir genkit-dist
    cp $GENKIT_DIST/* genkit-dist
    npm i --save ./genkit-dist/google-genkit-common-0.0.2.tgz
    npm i --save ./genkit-dist/google-genkit-flow-0.0.2.tgz
    npm i --save ./genkit-dist/google-genkit-ai-0.0.2.tgz
    npm i --save ./genkit-dist/google-genkit-providers-0.0.2.tgz 
    npm i --save ./genkit-dist/google-genkit-plugin-vertex-ai-0.0.2.tgz
    npm i --save-dev ./genkit-dist/google-genkit-tools-plugins-0.0.2.tgz
    npm i --save-dev ./genkit-dist/genkit-cli-0.0.2.tgz
    ```

1. Paste the following sample code into functions/src/index.ts file:
     ```javascript
     import { generate } from '@google-genkit/ai/generate';
     import { getProjectId } from '@google-genkit/common';
     import { configureGenkit } from '@google-genkit/common/config';
     import { run, runFlow } from '@google-genkit/flow';
     import { firebase } from '@google-genkit/providers/firebase';
     import { onFlow } from '@google-genkit/providers/firebase-functions';
     import { geminiPro, googleAI } from '@google-genkit/providers/google-ai';
     import { onRequest } from 'firebase-functions/v2/https';
     import * as z from 'zod';

     configureGenkit({
       plugins: [firebase({ projectId: getProjectId() }), googleAI()],
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

     export const triggerJokeFlow = onRequest(
       { invoker: 'private' },
       async (req, res) => {
          const { subject } = req.query;
         console.log('req.query', req.query);
         const op = await runFlow(jokeFlow, String(subject));
          console.log('operation', op);
         res.send(op);
       }
     );
     ```

2. Build your code by running: 
    
    ```
    npm run build
    ```

3. Run code locally: 

    ```
    npx genkit flow:run jokeFlow "\"banana\""
    ```

    Run Genkit Dev UI and try running the flow and explore traces:

    ```
    npx genkit start
    ```

    Open http://localhost:4000 in a browser.

4. Check that the "Default compute service account" has the necessary permissions to run your flow. By default it usually has an "Editor" role, but it's dependent on the org policy.

    Navigate to https://pantheon.corp.google.com/iam-admin/iam (make sure your project is selected) and search for the Principal ending with `-compute@developer.gserviceaccount.com`

    At the very least it will need the following roles: Cloud Datastore User, Vertex AI User, Logs Writer, Monitoring Metric Writer, Cloud Trace Agent.

    If you don't see it on the list then you'll need to manually grant it (`YOUT_PROJECT_NUMBER-compute@developer.gserviceaccount.com`) the necessary permissions.

    For reference: https://screencast.googleplex.com/cast/NTc2MDM0NjMzNjc4ODQ4MHw4ZWU2NDA2YS01Ng

5. Run: 

    ```
    firebase deploy
    ```

6. Run the flow via the REST API.

    You can  run the flow synchronously (blocking):

    ```
    curl -m 70 -X POST https://us-central1-$GCLOUD_PROJECT.cloudfunctions.net/jokeFlow -H "Authorization: bearer $(gcloud auth print-identity-token)" -H "Content-Type: application/json" -d '{"start": {"input": "banana"}}'
    ```

    You should see something like this:
    
    ```
    {"name":"bc042edd-efc4-48e9-8e36-23e4797e7a11","done":true,"result":{"response":"What did one banana say to the other?\n\nWe're about to split!"}}
    ```

    You can check the status of your flow by running:
    ```
    curl -m 70 -X POST https://us-central1-$GCLOUD_PROJECT.cloudfunctions.net/jokeFlow -H "Authorization: bearer $(gcloud auth print-identity-token)" -H "Content-Type: application/json" -d '{"state": {"flowId": "YOUR_FLOW_ID_FROM_PREVIOUS_RUN"}}'
    ```