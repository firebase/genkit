# Deploy flows using Cloud Functions for Firebase

Genkit includes a plugin that helps you deploy your flows to Cloud Functions for
Firebase. Flows, once deployed, are available as HTTPS endpoints and accessible
as callable functions using the Cloud Functions client libraries.

## Before you begin

*   Install the [Firebase CLI](/docs/cli).
*   You should be familiar with Genkit's concept of [flows](flows), and how to
    write them. The instructions on this page assume that you already have some
    flows defined, which you want to deploy.
*   It would be helpful, but not required, if you've already used Cloud
    Functions for Firebase before.

## 1. Set up a Firebase project

If you don't already have a Firebase project with TypeScript Cloud Functions set
up, follow these steps:

1.  Create a new Firebase project using the [Firebase
    console](https://console.firebase.google.com/) or choose an existing one.

1.  Upgrade the project to the Blaze plan, which is required to deploy Cloud
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

1.  Initialize a Firebase project in the directory:

    ```posix-terminal
    cd $PROJECT_ROOT

    firebase init genkit
    ```

    The rest of this page assumes that you've selected to write your functions
    in TypeScript, but you can also deploy your Genkit flows if you're using
    JavaScript.

## 2. Update flow definitions

After you've set up a Firebase project with Cloud Functions, you can copy or
write flow definitions in the project’s `functions/src` directory, and export
them in `index.ts`.

For your flows to be deployable, you will need to make some small changes to how
you define them. The core logic will remain the same, but you will add some
additional information to make them smoothly deployable and more secure once
deployed.

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

The following sections describe the changes you need to make before you can
deploy it.

### Define flows with onFlow

Instead of defining your flow with `Genkit.defineFlow()`, use the Firebase
plugin's `onFlow()` function. Using this function wraps your flow logic in a
Cloud Functions request handler, similar to
[`onCall`](/docs/functions/callable?gen=2nd#write_and_deploy_the_callable_function).

```ts
import { onFlow } from "@genkit-ai/firebase/functions";

export const generatePoem = onFlow(
  ai,
  {
    // ...
  },
  async (subject: string) => {
    // ...
  }
);
```

Note that `onFlow` isn't a method of `Genkit`, but rather a function that takes
a `Genkit` instance as its first parameter. Otherwise, the syntax is similar to
`defineFlow`.

### Define an authorization policy

All deployed flows, whether deployed to Firebase or not, should have an
authorization policy; without one, your potentially-expensive generative AI
flows would be invocable by anyone. To define an authorization policy, use the
`authPolicy` parameter in the flow definition:

```ts
import { firebaseAuth } from "@genkit-ai/firebase/auth";

export const generatePoem = onFlow(
  ai,
  {
    name: "generatePoem",
    // ...
    authPolicy: firebaseAuth((user, input) => {
      if (!user.email_verified) {
        throw new Error("Verified email required to run flow");
      }
    }),
  },
  async (subject: string) => {
    // ...
  }
);
```

This policy uses the `firebaseAuth()` helper to allow access only to registered
users of your app with verfied email addresses. On the client side, you need to
set the `Authorization: Bearer` header to a Firebase ID token that satisfies
your policy. The Cloud Functions client SDKs provide callable function methods
that automate this; see the section [Try the deployed flow](#example-client) for
an example.

### Make API credentials available to deployed flows 

Once deployed, your flows need some way to authenticate with any remote services
they rely on. Most flows will at a minimum need credentials for accessing the
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

      This step is important to prevent accidentally leaking your API key, which
      grants access to a potentially metered service.

      See [Store and access sensitive configuration information](/docs/functions/config-env?gen=2nd#secret-manager)
      for more information on managing secrets.

  1.  Edit `src/index.ts` and add the following after the existing imports:

      ```ts
      import {defineSecret} from "firebase-functions/params";
      const googleAIapiKey = defineSecret("GOOGLE_GENAI_API_KEY");
      ```

      Then, in the flow definition, declare that the cloud function needs access
      to this secret value:

      ```ts
      export const generatePoem = onFlow(
        {
          name: "generatePoem",
          // ...
          httpsOptions: {
            secrets: [googleAIapiKey],  // Add this line.
          },
        },
        async (subject) => {
          // ...
        }
      );
      ```

  Now, when you deploy this function, your API key will be stored in Cloud
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

### Set a CORS policy 

If you'll access your flow from a web app (which you will do in the [Try the
deployed flow](#example-client) section), in the `httpsOptions` parameter, set a
CORS policy:

```ts
export const generatePoem = onFlow(
  ai,
  {
    name: "generatePoem",
    // ...
    httpsOptions: {
      cors: '*',
    },
  },
  async (subject: string) => {
    // ...
  }
);
```

You will likely want a more restrictive policy for production apps, but this
will do for this tutorial.

### Complete example

After you've made all of the changes described above, your deployable flow will
look something like the following example:

```ts
const googleAIapiKey = defineSecret("GOOGLE_GENAI_API_KEY");

export const generatePoem = onFlow(
  ai,
  {
    name: "generatePoem",
    inputSchema: z.string(),
    outputSchema: z.string(),
    authPolicy: firebaseAuth((user, input) => {
      if (!user.email_verified) {
        throw new Error("Verified email required to run flow");
      }
    }),
    httpsOptions: {
      secrets: [googleAIapiKey],
      cors: '*',
    },
  },
  async (subject: string) => {
    const { text } = await ai.generate(`Compose a poem about ${subject}.`);
    return text;
  }
);
```

## 3. Deploy flows to Firebase

After you've defined flows using `onFlow`, you can deploy them as you would
deploy other Cloud Functions:

```posix-terminal
cd $PROJECT_ROOT

firebase deploy --only functions
```

You've now deployed the flow as a Cloud Function! But, you won't be able to
access your deployed endpoint with `curl` or similar, because of the flow's
authorization policy. Continue to the next section to learn how to securely
access the flow.

## Optional: Try the deployed flow {:#example-client}

To try out your flow endpoint, you can deploy the following minimal example web
app:

1.  In the [Project settings](https://console.firebase.google.com/project/_/settings/general)
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

## Optional: Run flows in the developer UI 

You can run flows defined using `onFlow` in the developer UI, exactly the same
way as you run flows defined using `defineFlow`, so there's no need to switch
between the two between deployment and development.

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

## Optional: Developing using Firebase Local Emulator Suite

Firebase offers a
[suite of emulators for local development](/docs/emulator-suite), which you can
use with Genkit.

To use the Genkit Dev UI with the Firebase Emulator Suite, start the Firebase emulators
like this:

```posix-terminal
npx genkit start -- firebase emulators:start --inspect-functions
```

This will run your code in the emulator and run the Genkit framework in
development mode, which launches and exposes the Genkit reflection API (but not
the Dev UI).

To see traces from Firestore in the Dev UI you can navigate to the Inspect tab
and toggle the "Dev/Prod" switch. When toggled to "prod" it will be loading
traces from firestore.
