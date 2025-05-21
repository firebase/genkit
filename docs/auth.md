# Authorization and integrity

When building any public-facing application, it's extremely important to protect
the data stored in your system. When it comes to LLMs, extra diligence is
necessary to ensure that the model is only accessing data it should, tool calls
are properly scoped to the user invoking the LLM, and the flow is being invoked
only by verified client applications.

Genkit provides mechanisms for managing authorization policies and
contexts. Flows running on Firebase can use an auth policy callback (or helper).
Alternatively, Firebase also provides auth context into the flow where it can
do its own checks. For non-Functions flows, auth can be managed and set
through middleware.

## Authorize within a Flow {:# authorize-within-flow}

Flows can check authorization in two ways: either the request binding
(e.g. `onCallGenkit` for Cloud Functions for Firebase or `express`) can enforce
authorization, or those frameworks can pass auth policies to the flow itself,
where the flow has access to the information for auth managed within the
flow.

```ts
import { genkit, z, UserFacingError } from 'genkit';

const ai = genkit({ ... });

export const selfSummaryFlow = ai.defineFlow( {
  name: 'selfSummaryFlow',
  inputSchema: z.object({ uid: z.string() }),
  outputSchema: z.string(),
}, async (input, { context }) => {
  if (!context.auth) {
    throw new UserFacingError('UNAUTHENTICATED', 'Unauthenticated');
  }
  if (input.uid !== context.auth.uid) {
    throw new UserFacingError('PERMISSION_DENIED', 'You may only summarize your own profile data.');
  }
  // Flow logic here...
});
```

It is up to the request binding to populate `context.auth` in this case. For
example, `onCallGenkit` automatically populates `context.auth`
(Firebase Authentication), `context.app` (Firebase App Check), and
`context.instanceIdToken` (Firebase Cloud Messaging). When calling a flow
manually, you can add your own auth context manually.

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

## Authorize using Cloud Functions for Firebase {:# authoring-using-cff}

The Cloud Functions for Firebase SDKs support Genkit including
integration with Firebase Auth / Google Cloud Identity Platform, as well as
built-in Firebase App Check support.

### User authentication
The `onCallGenkit()` wrapper provided by the Firebase Functions library has
built-in support for the Cloud Functions for Firebase
[client SDKs](https://firebase.google.com/docs/functions/callable?gen=2nd#call_the_function).
When you use these SDKs, the Firebase Auth header is automatically included as
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

When you use `onCallGenkit`, `context.auth` is returned as an object with
a `uid` for the user ID, and a `token` that is a
[DecodedIdToken](https://firebase.google.com/docs/reference/admin/node/firebase-admin.auth.decodedidtoken).
You can always retrieve this object at any time using `ai.currentContext()` as
noted earlier. When running this flow during development, you would pass the
user object in the same way:

```posix-terminal
genkit flow:run selfSummaryFlow '{"uid": "abc-def"}' --context '{"auth": {"admin": true}}'
```

Whenever you expose a Cloud Function to the wider internet, it is vitally
important that you use some sort of authorization mechanism to protect your data
and the data of your customers. With that said, there are times when you need
to deploy a Cloud Function with no code-based authorization checks (for example,
your Function is not world-callable but instead is protected by
[Cloud IAM](https://cloud.google.com/functions/docs/concepts/iam)).
Cloud Functions for Firebase lets you to do this using the `invoker` property,
which controls IAM access. The special value `'private'` leaves the function as
the default IAM setting, which means that only callers with the
[Cloud Run Invoker role](https://cloud.google.com/run/docs/reference/iam/roles)
can execute the function. You can instead provide the email address of a user
or service account that should be granted permission to call this exact
function.

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

#### Client integrity

Authentication on its own goes a long way to protect your app. But it's also
important to ensure that only your client apps are calling your functions. The
Firebase plugin for genkit includes first-class support for
[Firebase App Check](https://firebase.google.com/docs/app-check). Do this by
adding the following configuration options to your `onCallGenkit()`:

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
alongside the built-in flows.

Use a `ContextProvider` to populate context values such as `auth`, and to
provide a declarative policy or a policy callback. The Genkit
SDK provides `ContextProvider`s such as `apiKey`, and plugins may
expose them as well. For example, the `@genkit-ai/firebase/context` plugin
exposes a context provider for verifying Firebase Auth credentials and
populating them into context.

With code like the following, which might appear in a variety of
applications:

```ts
// Express app with a simple API key
import { genkit, z } from 'genkit';

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
```

You could secure a simple "flow server" express app by writing:

```ts
import { apiKey } from "genkit";
import { startFlowServer, withContextProvider } from "@genkit-ai/express";

startFlowServer({
  flows: [
    withContextProvider(selfSummaryFlow, apiKey(process.env.REQUIRED_API_KEY))
  ],
});
```

Or you could build a custom express application using the same tools:

```ts
import { apiKey } from "genkit";
import * as express from "express";
import { expressHandler } from "@genkit-ai/express;

const app = express();
// Capture but don't validate the API key (or its absence)
app.post('/summary', expressHandler(selfSummaryFlow, { contextProvider: apiKey()}))

app.listen(process.env.PORT, () => {
  console.log(`Listening on port ${process.env.PORT}`);
})
```

`ContextProvider`s abstract out the web framework, so these
tools work in other frameworks like Next.js as well. Here is an example of a
Firebase app built on Next.js.

```ts
import { appRoute } from "@genkit-ai/express";
import { firebaseContext } from "@genkit-ai/firebase";

export const POST = appRoute(selfSummaryFlow, { contextProvider: firebaseContext })
```

<!-- NOTE: Should we provide more docs? E.g. docs into various web frameworks and hosting services? -->
For more information about using Express, see the
[Cloud Run](/genkit/cloud-run) instructions.
