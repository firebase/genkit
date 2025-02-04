<!-- NOTE: prettier-ignore used in some snippets to allow copy/paste into Firebase Functions which
use https://github.com/firebase/firebase-tools/blob/master/templates/init/functions/javascript/_eslintrc -->

# Authorization and integrity

When building any public-facing application, it's extremely important to protect
the data stored in your system. When it comes to LLMs, extra diligence is
necessary to ensure that the model is only accessing data it should, tool calls
are properly scoped to the user invoking the LLM, and the flow is being invoked
only by verified client applications.

Firebase Genkit provides mechanisms for managing authorization policies and
contexts. Flows running on Firebase can use an auth policy callback (or helper)
or Firebase will provide auth context into the flow where it can do its own checks.
For non-Functions flows, auth can be managed and set as well through middleware.

## Basic flow authorization

Flows can check authorization in two ways: either the request binding (e.g. `onCallGenkit` for
Cloud Functions for Fireabse or `express`) can enforce authorization, or those frameworks
can pass auth policies to the flow itself where the flow will have access to the information
for auth managed within the flow.

```ts
import { genkit, z } from 'genkit';

const ai = genkit({ ... });

export const selfSummaryFlow = ai.defineFlow( {
  name: 'selfSummaryFlow',
  inputSchema: z.object({ uid: z.string() }),
  outputSchema: z.string(),
}, async (input, { context }) => {
  if (!context.auth) {
    throw new Error('Authorization required.');
  }
  if (input.uid !== context.auth.uid) {
    throw new Error('You may only summarize your own profile data.');
  }
  // Flow logic here...
});
```

It is up to the request binding to populate `context.auth` in this case. For example, `onCallGenkit`
will automatically populate `context.auth` (Firebase Authentication), `context.app` (Firebase App Check),
and `context.instanceIdToken` (Firebase Cloud Messaging). When calling a flow manually, you can add
your own auth context manually.

```ts
// Error: Authorization required.
await selfSummaryFlow({ uid: 'abc-def' });

// Error: You may only summarize your own profile data.
await selfSummaryFlow.run(
  { uid: 'abc-def' },
  {
    context: { auth: { uid: 'hij-klm' } },
  }
);

// Success
await selfSummaryFlow(
  { uid: 'abc-def' },
  {
    context: { auth: { uid: 'abc-def' } },
  }
);
```

When running with the Genkit Development UI, you can pass the Auth object by
entering JSON in the "Auth JSON" tab: `{"uid": "abc-def"}`.

You can also retrieve the auth context for the flow at any time within the flow
by calling `ai.currentContext()`, including in functions invoked by the flow:

```ts
import { genkit, z } from 'genkit';

const ai = genkit({ ... });;

async function readDatabase(uid: string) {
  const auth = ai.currentContext()?.auth;
  // Note: the shape of context.auth depends on the provider. onCallGenkit puts
  // claims information in auth.token
  if (auth?.token?.admin) {
    // Do something special if the user is an admin
  } else {
    // Otherwise, use the `uid` variable to retrieve the relevant document
  }
}

export const selfSummaryFlow = ai.defineFlow(
  {
    name: 'selfSummaryFlow',
    inputSchema: z.object({ uid: z.string() }),
    outputSchema: z.string(),
    authPolicy: ...
  },
  async (input) => {
    await readDatabase(input.uid);
  }
);
```

When testing flows with Genkit dev tools, you are able to specify this auth
object in the UI, or on the command line with the `--context` flag:

```posix-terminal
genkit flow:run selfSummaryFlow '{"uid": "abc-def"}' --context '{"auth": {"email_verified": true}}'
```

## Cloud Functions for Firebase integration

The Cloud Functions for Firebase SDK Firebase supports Genkit including integration with Firebase Auth / Google
Cloud Identity Platform as well as built-in Firebase App Check support.

### Authorization

The `onCallGenkit()` wrapper provided by the Firebase Functions library works natively with the
Cloud Functions for Firebase
[client SDKs](https://firebase.google.com/docs/functions/callable?gen=2nd#call_the_function).
When using the SDK, the Firebase Auth header will automatically be included as
long as your app client is also using the
[Firebase Auth SDK](https://firebase.google.com/docs/auth).
You can use Firebase Auth to protect your flows defined with `onCallGenkit()`:

<!-- prettier-ignore: see note above -->

```ts
import { genkit } from 'genkit';
import { onCallGenkit } from 'firebase-functions/https';

const ai = genkit({ ... });;

const selfSummaryFlow = ai.defineFlow({
  name: 'selfSummaryFlow',
  inputSchema: z.string(),
  outputSchema: z.string(),
}, async (input) => {
  // Flow logic here...
});

export const selfSummary = onCallGenkit({
  authPolicy: (auth) => auth?.token?.['email_verified'] && auth?.token?.['admin'],
}, selfSummaryFlow);
```

When using the `onCallGenkit`, `context.auth` will be returned as an object with
a `uid` for the user ID, and a `token` that is a
[DecodedIdToken](https://firebase.google.com/docs/reference/admin/node/firebase-admin.auth.decodedidtoken).
You can always retrieve this object at any time via `ai.currentContext()` as noted
above. When running this flow during development, you would pass the user object
in the same way:

```posix-terminal
genkit flow:run selfSummaryFlow '{"uid": "abc-def"}' --context '{"auth": {"admin": true}}'
```

Whenever you expose a Cloud Function to the wider internet, it is vitally
important that you use some sort of authorization mechanism to protect your data
and the data of your customers. With that said, there are times when you need
to deploy a Cloud Function with no code-based authorization checks (for example,
your Function is not world-callable but instead is protected by
[Cloud IAM](https://cloud.google.com/functions/docs/concepts/iam)). Cloud Functions
for Firebase allows you to do this using the `invoker` property, which controls
IAM access. The special value `'private'` leaves the function as the default IAM
setting, which means that only callers with the [Cloud Run Invoker role](https://cloud.google.com/run/docs/reference/iam/roles)
can execute the function. You can instead provide the email address of a user
or service account that should be granted permission to call this exact function.

<!-- prettier-ignore: see note above -->

```ts
import { onCallGenkit } from 'firebase-functions/https'

const selfSummaryFlow = ai.defineFlow({
  name: 'selfSummaryFlow',
  inputSchema: z.string(),
  outputSchema: z.string(),
}, async (input) => {
  // Flow logic here...
});

export const selfSummary = onCallGenkit({
  invoker: 'private',
}, selfSummaryFlow);
```

### Client integrity

Authentication on its own goes a long way to protect your app. But it's also
important to ensure that only your client apps are calling your functions. The
Firebase plugin for genkit includes first-class support for
[Firebase App Check](https://firebase.google.com/docs/app-check). Simply add
the following configuration options to your `onCallGenkit()`:

<!-- prettier-ignore: see note above -->

```ts
import { onCallGenkit } from 'firebase-functions/https';

const selfSummaryFlow = ai.defineFlow({
  name: 'selfSummaryFlow',
  inputSchema: z.string(),
  outputSchema: z.string(),
}, async (input) => {
  // Flow logic here...
});

export const selfSummary = onCallGenkit({
  // These two fields for app check. The consumeAppCheckToken option is for
  // replay protection, and requires additional client configuration. See the
  // App Check docs.
  enforceAppCheck: true,
  consumeAppCheckToken: true,

  authPolicy: ...,
}, selfSummaryFlow);
```

## Non-Firebase HTTP authorization

When deploying flows to a server context outside of Cloud Functions for
Firebase, you'll want to have a way to set up your own authorization checks
alongside the native flows. You have two options:

1.  Use whatever server framework you like, and pass the auth context through via
    the flow call as noted above.

1.  Use  `startFlowsServer()` available via `@genkit-ai/express` plugin and provide
    Express auth middleware in the flow server config:

    ```ts
    import { genkit, z } from 'genkit';
    import { startFlowServer, withAuth } from '@genkit-ai/express';

    const ai = genkit({ ... });;

    export const selfSummaryFlow = ai.defineFlow(
      {
        name: 'selfSummaryFlow',
        inputSchema: z.object({ uid: z.string() }),
        outputSchema: z.string(),
      },
      async (input) => {
        // Flow logic here...
      }
    );

    const authProvider = (req, res, next) => {
      const token = req.headers['authorization'];
      const user = yourVerificationLibrary(token);

      // Pass auth information to the flow
      req.auth = user;
      next();
    };

    startFlowServer({
      flows: [
        withAuth(selfSummaryFlow, authProvider, ({ auth, action, input, request }) => {
          if (!auth) {
            throw new Error('Authorization required.');
          }
          if (input.uid !== auth.uid) {
            throw new Error('You may only summarize your own profile data.');
          }
        })
      ],
    });  // Registers the middleware
    ```

    For more information about using Express, see the [Cloud Run](/genkit/cloud-run)
    instructions.

Please note, if you go with (1), you the `middleware` configuration option will
be ignored by when the flow is invoked directly.
