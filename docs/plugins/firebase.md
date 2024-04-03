# Firebase plugin

The Firebase plugin provides several integrations with Firebase services:

- Trace storage using Cloud Firestore
- Flow deployment using Cloud Functions
- Authorization policies for Firebase Authentication users

<!-- - State storage using Cloud Firestore -->

## Configuration

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { firebase } from '@genkit-ai/firebase';

configureGenkit({
  plugins: [firebase({ projectId: 'your-firebase-project' })],
});
```

The plugin requires you to specify your Firebase project ID. You can specify
your Firebase project ID in either of the following ways:

- Set `projectId` in the `firebase()` configuration object.

- Set the `GCLOUD_PROJECT` environment variable. If you're running your flow
  from a Google Cloud environment (Cloud Functions, Cloud Run, and so on),
  `GCLOUD_PROJECT` is automatically set to the project ID of the environment.

  If you set `GCLOUD_PROJECT`, you can omit the configuration parameter:
  `firebase()`

To provide Firebase credentials, you also need to set up Google Cloud
Application Default Credentials. To specify your credentials:

- If you're running your flow from a Google Cloud environment (Cloud Functions,
  Cloud Run, and so on), this is set automatically.

- For other environments:

  1.  Generate service account credentials for your Firebase project and
      download the JSON key file. You can do so on the
      [Service account](https://console.firebase.google.com/project/_/settings/serviceaccounts/adminsdk)
      page of the Firebase console.
  1.  Set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the file
      path of the JSON file that contains your service account key.

## Usage

This plugin provides several integrations with Firebase services, which you can
use together or individually.

### Cloud Firestore

You can use Cloud Firestore to store traces:

```js
import { firebase } from '@genkit-ai/firebase';

configureGenkit({
  plugins: [firebase()],
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
});
```

By default, the plugin stores traces in a collection called `genkit-traces` in
the project's default database. To change either setting:

```js
firebase({
  traceStore: {
    collection: 'your-collection';
    databaseId: 'your-db';
  }
})
```

### Cloud Functions

The plugin provides the `onFlow()` constructor, which creates a flow backed by a
Cloud Functions for Firebase HTTPS-triggered function. These functions conform
to Firebase's
[callable function interface](https://firebase.google.com/docs/functions/callable-reference) and you can use the
[Cloud Functions client SDKs](https://firebase.google.com/docs/functions/callable?gen=2nd#call_the_function)
to call them.

```js
import { firebase } from '@genkit-ai/firebase';
import { onFlow, noAuth } from '@genkit-ai/firebase/functions';

configureGenkit({
  plugins: [firebase()],
});

export const exampleFlow = onFlow(
  {
    name: 'exampleFlow',
    authPolicy: noAuth(), // WARNING: noAuth() creates an open endpoint!
  },
  async (prompt) => {
    // Flow logic goes here.

    return response;
  }
);
```

Deploy your flow using the Firebase CLI:

```posix-terminal
firebase deploy --only functions
```

The `onFlow()` function has some options not present in `defineFlow()`:

- `httpsOptions`: an [`HttpsOptions`](https://firebase.google.com/docs/reference/functions/2nd-gen/node/firebase-functions.https.httpsoptions)
  object used to configure your Cloud Function:

  ```js
  export const exampleFlow = onFlow(
    {
      name: 'exampleFlow',
      httpsOptions: {
        cors: '*',
      },
      // ...
    },
    async (prompt) => {
      // ...
    }
  );
  ```

- `enforceAppCheck`: when `true`, reject requests with missing or invalid [App Check](https://firebase.google.com/docs/app-check)
  tokens.

- `consumeAppCheckToken`: when `true`, invalidate the App Check token after verifying it.

  See [Replay protection](https://firebase.google.com/docs/app-check/cloud-functions#replay-protection).

### Firebase Auth

This plugin provides a helper function to create authorization policies around
Firebase Auth:

```js
import { firebaseAuth } from '@genkit-ai/firebase/auth';

export const exampleFlow = onFlow(
  {
    name: 'exampleFlow',
    authPolicy: firebaseAuth((user) => {
      if (!user.email_verified) throw new Error('Requires verification!');
    }),
  },
  async (prompt) => {
    // ...
  }
);
```

To define an auth policy, provide `firebaseAuth()` with a callback function that
takes a
[`DecodedIdToken`](https://firebase.google.com/docs/reference/admin/node/firebase-admin.auth.decodedidtoken)
as its only parameter. In this function, examine the user token and throw an
error if the user fails to meet any of the criteria you want to require.

See [Authorization and integrity](../auth.md) for a more thorough discussion of
this topic.
