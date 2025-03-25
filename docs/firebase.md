# Deploy flows using Cloud Functions for Firebase

Cloud Functions for Firebase has an `onCallGenkit` method that lets you
quickly create a [callable function](https://firebase.google.com/docs/functions/callable?gen=2nd)
with a Genkit action (e.g. a Flow). These functions can be called using
`genkit/beta/client`or the [Functions client SDK](https://firebase.google.com/docs/functions/callable?gen=2nd#call_the_function),
which automatically adds auth info.

## Before you begin

*   You should be familiar with Genkit's concept of [flows](flows), and how to
    write them. The instructions on this page assume that you already have some
    flows defined, which you want to deploy.
*   It would be helpful, but not required, if you've already used Cloud
    Functions for Firebase before.

## 1. Set up a Firebase project {:#setup}

If you don't already have a Firebase project with TypeScript Cloud Functions set
up, follow these steps:

1.  Create a new Firebase project using the [Firebase
    console](https://console.firebase.google.com/) or choose an existing one.

1.  Upgrade the project to the Blaze plan, which is required to deploy Cloud
    Functions.

1.  Install the [Firebase CLI](/docs/cli).

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

1.  Initialize a Firebase project in the directory:

    ```posix-terminal
    cd $PROJECT_ROOT

    firebase init genkit
    ```

    The rest of this page assumes that you've decided to write your functions
    in TypeScript, but you can also deploy your Genkit flows if you're using
    JavaScript.

## 2. Wrap the Flow in onCallGenkit {:#wrap-flow}

After you've set up a Firebase project with Cloud Functions, you can copy or
write flow definitions in the project’s `functions/src` directory, and export
them in `index.ts`.

For your flows to be deployable, you need to wrap them in `onCallGenkit`.
This method has all the features of the normal `onCall`. It automatically
supports both streaming and JSON responses.

Suppose you have the following flow:

```ts
const generatePoemFlow = ai.defineFlow(
  {
    name: "generatePoem",
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject: string) => {
    const { text } = await ai.generate(`Compose a poem about ${subject}.`);
    return text;
  }
);
```

You can expose this flow as a callable function using `onCallGenkit`:

```ts
import { onCallGenkit } from 'firebase-functions/https';

export generatePoem = onCallGenkit(generatePoemFlow);
```

### Make API credentials available to deployed flows

Once deployed, your flows need some way to authenticate with any remote services
they rely on. Most flows need, at a minimum, credentials for accessing the
model API service they use.

For this example, do one of the following, depending on the model provider you
chose:

- {Gemini (Google AI)}

    1.  Make sure Google AI is [available in your
        region](https://ai.google.dev/available_regions).

    1.  [Generate an API key](https://aistudio.google.com/app/apikey) for the
        Gemini API using Google AI Studio.

    1.  Store your API key in Cloud Secret Manager:

        ```posix-terminal
        firebase functions:secrets:set GOOGLE_GENAI_API_KEY
        ```

        This step is important to prevent accidentally leaking your API key,
        which grants access to a potentially metered service.

        See [Store and access sensitive configuration information](/docs/functions/config-env?gen=2nd#secret-manager)
        for more information on managing secrets.

    1.  Edit `src/index.ts` and add the following after the existing imports:

        ```ts
        import {defineSecret} from "firebase-functions/params";
        const googleAIapiKey = defineSecret("GOOGLE_GENAI_API_KEY");
        ```

        Then, in the flow definition, declare that the cloud function needs
        access to this secret value:

        ```ts
        export const generatePoem = onCallGenkit({
          secrets: [googleAIapiKey]
        }, generatePoemFlow);
        ```

  Now, when you deploy this function, your API key is stored in Cloud
  Secret Manager, and available from the Cloud Functions environment.

- {Gemini (Vertex AI)}

    1.  In the Cloud console, [Enable the Vertex AI
        API](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=_)
        for your Firebase project.

    1.  On the [IAM](https://console.cloud.google.com/iam-admin/iam?project=_)
        page, ensure that the **Default compute service account** is granted the
        **Vertex AI User** role.

The only secret you need to set up for this tutorial is for the model provider,
but in general, you must do something similar for each service your flow uses.

### Add App Check enforcement

[Firebase App Check](https://firebase.google.com/docs/app-check) uses a
built-in attestation mechanism to verify that your API is only being called by
your application. `onCallGenkit` supports App Check enforcement declaratively.

```ts
export const generatePoem = onCallGenkit({
  enforceAppCheck: true,
  // Optional. Makes App Check tokens only usable once. This adds extra security
  // at the expense of slowing down your app to generate a token for every API
  // call
  consumeAppCheckToken: true,
}, generatePoemFlow);
```

### Set a CORS policy

Callable functions default to allowing any domain to call your function. If you
want to customize the domains that can do this, use the `cors` option.
With proper authentication (especially App Check), CORS is often unnecessary.

```ts
export const generatePoem = onCallGenkit({
  cors: 'mydomain.com',
}, generatePoemFlow);
```

### Complete example

After you've made all of the changes described earlier, your deployable flow
looks something like the following example:

```ts
import { genkit } from 'genkit';
import { onCallGenkit, hasClaim } from 'firebase-functions/https';
import { defineSecret } from 'firebase-functions/params';

const apiKey = defineSecret("GOOGLE_GENAI_API_KEY");

const generatePoemFlow = ai.defineFlow({
  name: "generatePoem",
  inputSchema: z.string(),
  outputSchema: z.string(),
}, async (subject: string) => {
  const { text } = await ai.generate(`Compose a poem about ${subject}.`);
  return text;
});

export const generateFlow = onCallGenkit({
  secrets: [apiKey],
  authPolicy: hasClaim("email_verified"),
  enforceAppCheck: true,
}, generatePoemFlow);
```

## 3. Deploy flows to Firebase {:#deploy-flows}

After you've defined flows using `onCallGenkit`, you can deploy them the same
way you would deploy other Cloud Functions:

```posix-terminal
cd $PROJECT_ROOT

firebase deploy --only functions
```

You've now deployed the flow as a Cloud Function! But you can't
access your deployed endpoint with `curl` or similar, because of the flow's
authorization policy. The next section explains how to securely  access the
flow.

## Optional: Try the deployed flow {:#example-client}

To try out your flow endpoint, you can deploy the following minimal example web
app:

1.  In the [Project settings](https://console.firebase.google.com/project/_/settings/general)
    section of the Firebase console, add a new web app, selecting the option to
    also set up Hosting.

1.  In the
    [Authentication](https://console.firebase.google.com/project/_/authentication/providers)
    section of the Firebase console, enable the **Google** provider, used in
    this example.

1.  In your project directory, set up Firebase Hosting, where you will deploy
    the sample app:

    ```posix-terminal
    cd $PROJECT_ROOT

    firebase init hosting
    ```

    Accept the defaults for all of the prompts.

1.  Replace `public/index.html` with the following:

    ```html
    <!DOCTYPE html>
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
          <button id="generatePoem">Compose a poem on this subject</button>
          <p id="generatedPoem"></p>
        </div>
        <script type="module">
          import { initializeApp } from "https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js";
          import {
            getAuth,
            onAuthStateChanged,
            GoogleAuthProvider,
            signInWithPopup,
          } from "https://www.gstatic.com/firebasejs/11.0.1/firebase-auth.js";
          import {
            getFunctions,
            httpsCallable,
          } from "https://www.gstatic.com/firebasejs/11.0.1/firebase-functions.js";

          const firebaseConfig = await fetch("/__/firebase/init.json");
          initializeApp(await firebaseConfig.json());

          async function generatePoem() {
            const poemFlow = httpsCallable(getFunctions(), "generatePoem");
            const subject = document.querySelector("#subject").value;
            const response = await poemFlow(subject);
            document.querySelector("#generatedPoem").innerText = response.data;
          }

          function signIn() {
            signInWithPopup(getAuth(), new GoogleAuthProvider());
          }

          document.querySelector("#signinBtn").addEventListener("click", signIn);
          document
            .querySelector("#generatePoem")
            .addEventListener("click", generatePoem);

          const signinEl = document.querySelector("#signin");
          const genkitEl = document.querySelector("#callGenkit");

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

## Optional: Run flows in the developer UI {:#run-flows}

You can run flows defined using `onCallGenkit` in the developer UI, exactly the
same way as you run flows defined using `defineFlow`, so there's no need to
switch between the two between deployment and development.

```posix-terminal
cd $PROJECT_ROOT/functions

npx genkit start -- npx tsx --watch src/index.ts
```

or

```posix-terminal
cd $PROJECT_ROOT/functions

npm run genkit:start
```

You can now navigate to the URL printed by the `genkit start` command to access.

## Optional: Developing using Firebase Local Emulator Suite {:#firebase-local}

Firebase offers a
[suite of emulators for local development](/docs/emulator-suite), which you can
use with Genkit.

To use the Genkit Dev UI with the Firebase Emulator Suite, start the Firebase
emulators as follows:

```posix-terminal
npx genkit start -- firebase emulators:start --inspect-functions
```

This command runs your code in the emulator, and runs the Genkit framework in
development mode. This launches and exposes the Genkit reflection API (but not
the Dev UI).

To see traces from Firestore in the Dev UI, you can navigate to the _Inspect_
tab and toggle the *Dev/Prod* switch. When toggled to _prod_ it loads
traces from firestore.
