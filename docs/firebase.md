# Genkit with Firebase Cloud Functions

Firebase Genkit includes a plugin that helps you deploy your flows to Firebase
Cloud Functions. This page, as an example, walks you through the process of
deploying the default sample flow to Firebase.

## Deploy a flow as a Cloud Function

1.  Install the required tools:

    1.  Make sure you are using Node.js version 18 or higher (run `node --version` to
        check).

    1.  Install the [Firebase CLI](https://firebase.google.com/docs/cli).

1.  Create a new Firebase project using the [Firebase console](https://console.firebase.google.com/) or choose an existing one.

    Upgrade the project to the Blaze plan, which is required to deploy Cloud
    Functions.

1.  Log in with the Firebase CLI:

    ```posix-terminal
    firebase login

    firebase login --reauth # alternative, if necessary

    firebase login --no-localhost # if running in a remote shell
    ```

1.  Create a new project directory:

    ```posix-terminal
    export PROJECT_ROOT=~/tmp/genkit-firebase-project1

    mkdir -p $PROJECT_ROOT
    ```

1.  Initialize a Firebase project in the folder:

    ```posix-terminal
    cd $PROJECT_ROOT

    firebase init
    ```

    - Select the project you created earlier.
    - Select **Functions** as the only feature to set up (for now).
    - Select **TypeScript** as the functions language.

    Accept the defaults for the remaining prompts.

1.  Initialize Genkit in your Firebase project:

    ```posix-terminal
    cd $PROJECT_ROOT/functions

    genkit init
    ```

    - Select **Firebase** as the deployment platform.
    - Select the model provider you want to use.

    Accept the defaults for the remaining prompts. The `genkit` tool will create
    some sample source files to get you started developing your own AI flows.
    For the rest of this tutorial, however, you'll just deploy the sample flow.

1.  Make API credentials available to your Cloud Function. Do one of the
    following, depending on the model provider you chose:

    - {Gemini (Google AI)}

      1.  Make sure Google AI is [available in your region](https://ai.google.dev/available_regions).

      1.  [Generate an API key](https://aistudio.google.com/app/apikey) for the
          Gemini API using Google AI Studio.

      1.  Set the `GOOGLE_GENAI_API_KEY` environment variable to your key:

          ```posix-terminal
          export GOOGLE_GENAI_API_KEY=<your API key>
          ```

      1.  Edit `src/index.ts` and add the following after the existing imports:

          ```js
          import { defineSecret } from 'firebase-functions/params';
          defineSecret('GOOGLE_GENAI_API_KEY');
          ```

          Now, when you deploy this function, your API key will be stored in
          Cloud Secret Manager, and available from the Cloud Functions
          environment.

    - {Gemini (Vertex AI)}

      1.  In the Cloud console,
          [Enable the Vertex AI API](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=_)
          for your Firebase project.

      1.  On the [IAM](https://console.cloud.google.com/iam-admin/iam?project=_)
          page, ensure that the **Default compute service account** is granted
          the **Vertex AI User** role.

      1.  **Optional**: If you want to run your flow locally, as in the next
          step, set some additional environment variables and use the
          [`gcloud`](https://cloud.google.com/sdk/gcloud) tool to set up
          application default credentials:

          ```posix-terminal
          export GCLOUD_PROJECT=<your project ID>

          export GCLOUD_LOCATION=us-central1

          gcloud auth application-default login
          ```

    The only secret you need to set up for this tutorial is for the model
    provider, but in general, you must do something similar for each service
    your flow uses.

1.  If you'll access your flow from a web app (which you will be doing in the
    next section), in the `httpsOptions` parameter, set a CORS policy:

    ```js
    export const jokeFlow = onFlow(
      {
        name: 'jokeFlow',
        // ...
        httpsOptions: { cors: '*' }, // Add this line.
      },
      async (subject) => {
        // ...
      }
    );
    ```

    You will likely want a more restrictive policy for production apps, but this
    will do for this tutorial.

1.  **Optional**: Try your flow in the developer UI:

    1.  Start the UI:

        ```posix-terminal
        cd $PROJECT_ROOT/functions

        genkit start
        ```

    2.  In the developer UI (http://localhost:4000/), run the flow:

        1.  Click **jokeFlow**.

        2.  On the **Input JSON** tab, provide a subject for the model:

            ```json
            "AI app developers"
            ```

        3.  On the **Auth JSON** tab, provide a simulated auth object:

            ```json
            {
              "uid": 0,
              "email_verified": true
            }
            ```

        4.  Click **Run**.

1.  If everything's working as expected so far, you can deploy the flow:

    ```posix-terminal
    cd $PROJECT_ROOT

    firebase deploy --only functions
    ```

You've now deployed the flow as a Cloud Function! But, you won't be able to
access your deployed endpoint with `curl` or similar, because of the flow's
authorization policy. Continue to the next section to learn how to securely
access the flow.

## Try the deployed flow

It is critical that every flow you deploy sets an authorization policy. Without
one, your potentially-expensive generative AI flows would be invocable by
anyone.

The default sample flow has an authorization policy like the following:

```js
firebaseAuth((user) => {
  if (!user.email_verified) {
    throw new Error('Verified email required to run flow');
  }
});
```

This policy uses the `firebaseAuth()` helper to allow access only to registered
users of your app with verfied email addresses. On the client side, you need to
set the `Authorization: Bearer` header to a Firebase ID token that satisfies
your policy. The Cloud Functions client SDKs provide
[callable function](https://firebase.google.com/docs/functions/callable?gen=2nd#call_the_function)
methods that automate this.

To try out your flow endpoint, you can deploy the following minimal example web
app:

1.  In the
    [Project settings](https://console.firebase.google.com/project/_/settings/general)
    section of the Firebase console, add a new web app, selecting the option to
    also set up Hosting.

1.  In the
    [Authentication](https://console.firebase.google.com/project/_/authentication/providers)
    section of the Firebase console, enable the **Google** provider, which you
    will use in this example.

1.  In your project directory, set up Firebase Hosting, where you will deploy
    the sample app:

    ```posix-terminal
    cd $PROJECT_ROOT

    firebase init hosting
    ```

    Accept the defaults for all of the prompts.

1.  Replace `public/index.html` with the following:

    ```html
    <!doctype html>
    <html>
      <head>
        <title>Genkit demo</title>
      </head>
      <body>
        <div id="signin" hidden>
          <button id="signinBtn">Sign in with Google</button>
        </div>
        <div id="callGenkit" hidden>
          Subject: <input type="text" id="subject" />
          <button id="tellJoke">Tell me a joke</button>
          <p id="joke"></p>
        </div>
        <script type="module">
          import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.10.0/firebase-app.js';
          import {
            getAuth,
            onAuthStateChanged,
            GoogleAuthProvider,
            signInWithPopup,
          } from 'https://www.gstatic.com/firebasejs/10.10.0/firebase-auth.js';
          import {
            getFunctions,
            httpsCallable,
          } from 'https://www.gstatic.com/firebasejs/10.10.0/firebase-functions.js';

          const firebaseConfig = await fetch('/__/firebase/init.json');
          initializeApp(await firebaseConfig.json());

          async function generateJoke() {
            const jokeFlow = httpsCallable(getFunctions(), 'jokeFlow');
            const subject = document.querySelector('#subject').value;
            const response = await jokeFlow(subject);
            document.querySelector('#joke').innerText = response.data;
          }

          function signIn() {
            signInWithPopup(getAuth(), new GoogleAuthProvider());
          }

          document
            .querySelector('#signinBtn')
            .addEventListener('click', signIn);
          document
            .querySelector('#tellJoke')
            .addEventListener('click', generateJoke);

          const signinEl = document.querySelector('#signin');
          const genkitEl = document.querySelector('#callGenkit');

          onAuthStateChanged(getAuth(), (user) => {
            if (!user) {
              signinEl.hidden = false;
              genkitEl.hidden = true;
            } else {
              signinEl.hidden = true;
              genkitEl.hidden = false;
            }
          });
        </script>
      </body>
    </html>
    ```

1.  Deploy the web app and Cloud Function:

    ```posix-terminal
    cd $PROJECT_ROOT

    firebase deploy
    ```

Open the web app by visiting the URL printed by the `deploy` command. The app
requires you to sign in with a Google account, after which you can initiate
endpoint requests.

## Developing using Firebase Local Emulator Suite

Firebase offers a [suite of emulators for local development](https://firebase.google.com/docs/emulator-suite), which you can use with Genkit.

To use Genkit with the Firebase Emulator Suite, start the the Firebase emulators like this:

```bash
GENKIT_ENV=dev firebase emulators:start --inspect-functions
```

This will run your code in the emulator and run the Genkit framework in development mode, which launches and exposes the Genkit reflection API (but not the Dev UI).

Then, launch the Genkit Dev UI with the `--attach` option to connect it to your code running inside the Firebase Emulator:

```bash
genkit start --attach http://localhost:3100 --port 4001
```

To see traces from Firestore in the Dev UI you can navigate to the Inspect tab and toggle the "Dev/Prod" switch. When toggled to "prod" it will be loading traces from firestore.