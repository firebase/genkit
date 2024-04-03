# Genkit with Firebase

1.  Install required tools

    1.  Make sure you are using node version 18 or higher (run `node --version`
        to check).

    1.  Install [firebase CLI](https://firebase.google.com/docs/cli) and
        [gcloud cli](https://cloud.google.com/sdk/docs/install)

1.  Login to Firebase

    ```posix-terminal
    firebase login

    firebase login --reauth # alternative, if necessary

    firebase login --no-localhost # if running in cloud shell
    ```

1.  Create a new Firebase project using the [Firebase
    console](https://console.firebase.google.com/) or select an existing one.
    Make sure the project is on Blaze plan (i.e. has billing account). Enable
    Firebase Auth with the Google auth provider.

1.  After you have created / picked one, run the following to set an env var
    with your project ID and set the project as your default:

    ```posix-terminal
    export GCLOUD_PROJECT=<your-cloud-project>
    ```

1.  Create a new folder for the project

    ```posix-terminal
    export GENKIT_PROJECT_HOME=~/tmp/genkit-firebase-project1

    mkdir -p $GENKIT_PROJECT_HOME

    cd $GENKIT_PROJECT_HOME
    ```

1.  Initialize firebase project in the folder

    ```posix-terminal
    firebase init functions --project $GCLOUD_PROJECT
    ```

    For functions language pick _TypeScript_.

    Up to you whether you want ESLint, but for prototyping it might be getting
    in the way, recommend selecting "n".

    Feel free to say yes to installing dependencies with npm.

1.  Initialize Firebase Hosting, to test your callable flow

    ```posix-terminal
    firebase init hosting
    ```

    Keep all the default options (your assets will go into `./public`)

1.  The sample uses the Google Generative AI API. You will need an API key from
    AI Studio, you can get one here: https://aistudio.google.com/app/apikey

    ```posix-terminal
    export GOOGLE_API_KEY=xyzYourKeyHere
    ```

1.  Create a `functions/.env` file and add `GOOGLE_API_KEY=xyzYourKeyHere`.

1.  Initialize Genkit in your Firebase project:

    Download and unzip [genkit-dist.zip](https://bit.ly/genkit-dist) (e.g. `$HOME/Downloads/genkit-dist`).

    Start by installing Genkit CLI

    ```posix-terminal
    cd functions

    npm i --save -D $HOME/Downloads/genkit-dist/genkit-cli-0.0.7.tgz $HOME/Downloads/genkit-dist/genkit-ai-tools-plugins-0.0.7.tgz
    ```

    Then run:

    ```posix-terminal
    npx genkit init -d $HOME/Downloads/genkit-dist/genkit-dist.zip
    ```

    Select `firebase` as the deployment platform option and Google AI as the model. If Google AI is not available in your region (see https://ai.google.dev/available_regions) consider using Vertex AI.

1.  Paste the following sample code into `functions/src/index.ts` file:

    ```javascript
    import { generate } from '@genkit-ai/ai';
    import { configureGenkit } from '@genkit-ai/core';
    import { run } from '@genkit-ai/flow';
    import { firebase } from '@genkit-ai/firebase';
    import { firebaseAuth } from '@genkit-ai/firebase/auth';
    import { onFlow } from '@genkit-ai/firebase/functions';
    import { geminiPro, googleGenAI } from '@genkit-ai/google-genai';
    import * as z from 'zod';

    configureGenkit({
      plugins: [firebase(), googleGenAI()],
      flowStateStore: 'firebase',
      traceStore: 'firebase',
      enableTracingAndMetrics: true,
      logLevel: 'debug',
    });

    export const jokeFlow = onFlow(
      {
        name: 'jokeFlow',
        inputSchema: z.string(),
        outputSchema: z.string(),
        authPolicy: firebaseAuth((user) => {
          if (!user.email_verified) throw new Error('Requires verification!');
        }),
        httpsOptions: {
          cors: '*',
        },
      },
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

````

1.  Build your code by running:

  ```posix-terminal
  npm run build
  ```

1.  Run your code locally:

  ```posix-terminal
  npx genkit flow:run jokeFlow "\"banana\"" --auth "{\"email_verified\": true}"
  ```

  Run Genkit Dev UI and try running the flow and explore traces:

  ```posix-terminal
  npx genkit start
  ```

  Open http://localhost:4000 in a browser.

1.  Check that the _Default compute service account_ has the necessary
  permissions to run your Genkit flow. By default it usually has an _Editor_
  role, but it's dependent on the organisation policy.

  Navigate to https://console.cloud.google.com/iam-admin/iam (make sure your
  project is selected) and search for the principal ending with
  `-compute@developer.gserviceaccount.com`

  At the very least it will need the following roles: _Cloud Datastore User_,
  _Vertex AI User_, _Logs Writer_, _Monitoring Metric Writer_, _Cloud Trace
  Agent_.

  If you don't see it on the list then you'll need to manually grant it
  (`YOUT_PROJECT_NUMBER-compute@developer.gserviceaccount.com`) the necessary
  permissions.

1.  Create a simple web app to get a Firebase Auth context. Go to the Firebase
  Console and create a new Web app, and copy the config JS blob that is given.

  Create `public/index.html` with the following contents:
  ```html
  <body>
      <!-- Insert this script at the bottom of the HTML, but before you use any Firebase services -->
      <script type="module">
          import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.9.0/firebase-app.js'

          // Add Firebase products that you want to use
          import { getAuth, signInWithPopup, GoogleAuthProvider } from 'https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js'
          import { getFunctions, httpsCallable } from 'https://www.gstatic.com/firebasejs/10.9.0/firebase-functions.js'

          const firebaseConfig = {...}; // From the Console
          const app = initializeApp(firebaseConfig);

          const auth = getAuth();
          const fns = getFunctions();

          window.login = () => {
              signInWithPopup(auth, new GoogleAuthProvider());
          };

          window.tellJoke = (subject) => {
              const callable = httpsCallable(fns, 'jokeFlow')
              return callable(subject);
          }
      </script>
  </body>
  ```


1.  Run:

  ```posix-terminal
  firebase deploy --only functions
  firebase serve --only hosting
  ```

1.  Run the flow from your web app. Go to http://localhost:5000 in your browser.

  Open developer tools to the JS console. First try running the flow without
  logging in:

  ```js
  await tellJoke('Banana');
  ```

  Now try logging in first.
  ```js
  login();

  // Follow the login prompt, then run:
  await tellJoke('Banana');
  ```

  You can read more about the Genkit integration with Firebase Auth in the
  [authorization docs](/genkit/auth).
````
