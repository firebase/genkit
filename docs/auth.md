<!-- NOTE: prettier-ignore used in some snippets to allow copy/paste into Firebase Functions which
use https://github.com/firebase/firebase-tools/blob/master/templates/init/functions/javascript/_eslintrc -->

# Authorization and integrity

When building any public-facing application, it's extremely important to protect
the data stored in your system. When it comes to LLMs, extra diligence is
necessary to ensure that the model is only accessing data it should, tool calls
are properly scoped to the user invoking the LLM, and the flow is being invoked
only by verified client applications.

Firebase Genkit provides mechanisms for managing authorization policies and
contexts. For flows running on Cloud Functions for Firebase, developers are
required to provide an auth policy or else explicitly acknowledge the lack of
one. For non-Functions flows, auth can be managed and set as well, but requires
a bit more manual integration.

## Basic flow authorization

All flows can define an `authPolicy` in their config. An auth policy is a function that tests if certain criteria (defined by you) are met, and throws an exception if any test fails.
If this field is set, it is executed before the flow is invoked:

```ts
import { genkit, z } from 'genkit';

const ai = genkit({ ... });

export const selfSummaryFlow = ai.defineFlow(
  {
    name: 'selfSummaryFlow',
    inputSchema: z.object({ uid: z.string() }),
    outputSchema: z.string(),
    authPolicy: (auth, input) => {
      if (!auth) {
        throw new Error('Authorization required.');
      }
      if (input.uid !== auth.uid) {
        throw new Error('You may only summarize your own profile data.');
      }
    },
  },
  async (input) => {
    // Flow logic here...
  }
);
```

When executing this flow, you _must_ provide an auth object using `withLocalAuthContext` or else you'll
receive an error:

```ts
// Error: Authorization required.
await selfSummaryFlow({ uid: 'abc-def' });

// Error: You may only summarize your own profile data.
await selfSummaryFlow(
  { uid: 'abc-def' },
  {
    withLocalAuthContext: { uid: 'hij-klm' },
  }
);

// Success
await selfSummaryFlow(
  { uid: 'abc-def' },
  {
    withLocalAuthContext: { uid: 'abc-def' },
  }
);
```

When running with the Genkit Development UI, you can pass the Auth object by
entering JSON in the "Auth JSON" tab: `{"uid": "abc-def"}`.

You can also retrieve the auth context for the flow at any time within the flow
by calling `getFlowAuth()`, including in functions invoked by the flow:

```ts
import { genkit, z } from 'genkit';

const ai = genkit({ ... });;

async function readDatabase(uid: string) {
  const auth = ai.getAuthContext();
  if (auth?.admin) {
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
object in the UI, or on the command line with the `--auth` flag:

```posix-terminal
genkit flow:run selfSummaryFlow '{"uid": "abc-def"}' --auth '{"uid": "abc-def"}'
```

## Cloud Functions for Firebase integration

The Firebase plugin provides convenient integration with Firebase Auth / Google
Cloud Identity Platform as well as built-in Firebase App Check support.

### Authorization

The `onFlow()` wrapper provided by the Firebase plugin works natively with the
Cloud Functions for Firebase
[client SDKs](https://firebase.google.com/docs/functions/callable?gen=2nd#call_the_function).
When using the SDK, the Firebase Auth header will automatically be included as
long as your app client is also using the
[Firebase Auth SDK](https://firebase.google.com/docs/auth).
You can use Firebase Auth to protect your flows defined with `onFlow()`:

<!-- prettier-ignore: see note above -->

```ts
import { genkit } from 'genkit';
import { firebaseAuth } from '@genkit-ai/firebase';
import { onFlow } from '@genkit-ai/firebase/functions';

const ai = genkit({ ... });;

export const selfSummaryFlow = onFlow(
  ai,
  {
    name: 'selfSummaryFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
    authPolicy: firebaseAuth((user) => {
      if (!user.email_verified && !user.admin) {
        throw new Error('Email not verified');
      }
    }),
  },
  async (input) => {
        // Flow logic here...
  }
);
```

When using the Firebase Auth plugin, `user` will be returned as a
[DecodedIdToken](https://firebase.google.com/docs/reference/admin/node/firebase-admin.auth.decodedidtoken).
You can always retrieve this object at any time via `getFlowAuth()` as noted
above. When running this flow during development, you would pass the user object
in the same way:

```posix-terminal
genkit flow:run selfSummaryFlow '{"uid": "abc-def"}' --auth '{"admin": true}'
```

By default the Firebase Auth plugin requires the auth header to be sent by the
client, but in cases where you wish to allow unauthenticated access with special
handling for authenticated users (upselling features, say), then you can
configure the policy like so:

<!-- prettier-ignore: see note above  -->

```ts
authPolicy: firebaseAuth((user) => {
  if (user && !user.email_verified) {
    throw new Error("Logged in users must have verified emails");
  }
}, {required: false}),
```

Whenever you expose a Cloud Function to the wider internet, it is vitally
important that you use some sort of authorization mechanism to protect your data
and the data of your customers. With that said, there are times when you need
to deploy a Cloud Function with no code-based authorization checks (for example,
your Function is not world-callable but instead is protected by
[Cloud IAM](https://cloud.google.com/functions/docs/concepts/iam)). The
`authPolicy` field is always required when using `onFlow()`, but you can
indicate to the library that you are forgoing authorization checks by using the
`noAuth()` function:

<!-- prettier-ignore: see note above -->

```ts
import { onFlow, noAuth } from "@genkit-ai/firebase/functions";

export const selfSummaryFlow = onFlow(
  ai,
  {
    name: "selfSummaryFlow",
    inputSchema: z.string(),
    outputSchema: z.string(),
    // WARNING: Only do this if you have some other gatekeeping in place, like
    // Cloud IAM!
    authPolicy: noAuth(),
  },
  async (input) => {
        // Flow logic here...
  }
);
```

### Client integrity

Authentication on its own goes a long way to protect your app. But it's also
important to ensure that only your client apps are calling your functions. The
Firebase plugin for genkit includes first-class support for
[Firebase App Check](https://firebase.google.com/docs/app-check). Simply add
the following configuration options to your `onFlow()`:

<!-- prettier-ignore: see note above -->

```ts
import { onFlow } from "@genkit-ai/firebase/functions";

export const selfSummaryFlow = onFlow(
  ai,
  {
    name: "selfSummaryFlow",
    inputSchema: z.string(),
    outputSchema: z.string(),

    // These two fields for app check. The consumeAppCheckToken option is for
    // replay protection, and requires additional client configuration. See the
    // App Check docs.
    enforceAppCheck: true,
    consumeAppCheckToken: true,

    authPolicy: ...,
  },
  async (input) => {
        // Flow logic here...
  }
);
```

## Non-Firebase HTTP authorization

When deploying flows to a server context outside of Cloud Functions for
Firebase, you'll want to have a way to set up your own authorization checks
alongside the native flows. You have two options:

1.  Use whatever server framework you like, and pass the auth context through via
    the flow call as noted above.

1.  Use the built-in `startFlowsServer()` and provide Express middleware in the
    flow config:

    ```ts
    import { genkit, z } from 'genkit';

    const ai = genkit({ ... });;

    export const selfSummaryFlow = ai.defineFlow(
      {
        name: 'selfSummaryFlow',
        inputSchema: z.object({ uid: z.string() }),
        outputSchema: z.string(),
        middleware: [
          (req, res, next) => {
            const token = req.headers['authorization'];
            const user = yourVerificationLibrary(token);

            // Pass auth information to the flow
            req.auth = user;
            next();
          }
        ],
        authPolicy: (auth, input) => {
          if (!auth) {
            throw new Error('Authorization required.');
          }
          if (input.uid !== auth.uid) {
            throw new Error('You may only summarize your own profile data.');
          }
        }
      },
      async (input) => {
        // Flow logic here...
      }
    );

    ai.startFlowServer({
      flows: [selfSummaryFlow],
    });  // Registers the middleware
    ```

    For more information about using Express, see the [Cloud Run](/genkit/express)
    instructions.

Please note, if you go with (1), you the `middleware` configuration option will
be ignored by when the flow is invoked directly.
