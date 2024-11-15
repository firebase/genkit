# Deploy flows using Cloud Run

You can deploy Genkit flows as HTTPS endpoints using Cloud Run. Cloud Run has
several deployment options, including container based deployment; this page will
explain how to deploy your flows directly from code.

## Before you begin

*   Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).
*   You should be familiar with Genkit's concept of [flows](flows), and how to
    write them. This page assumes that you already have flows that you want to
    deploy.
*   It would be helpful, but not required, if you've already used Google Cloud
    and Cloud Run before.

## 1. Set up a Google Cloud project

If you don't already have a Google Cloud project set up, follow these steps:

1.  Create a new Google Cloud project using the
    [Cloud console](https://console.cloud.google.com) or choose an existing one.

1.  Link the project to a billing account, which is required for Cloud Run.

1.  Configure the Google Cloud CLI to use your project:

    ```posix-terminal
    gcloud init
    ```

## 2. Prepare your Node project for deployment

For your flows to be deployable, you will need to make some small changes to
your project code:

### Add start and build scripts to package.json 

When deploying a Node.js project to Cloud Run, the deployment tools expect your
project to have a `start` script and, optionally, a `build` script. For a
typical TypeScript project, the following scripts are usually adequate:

```json
"scripts": {
  "start": "node lib/index.js",
  "build": "tsc"
},
```

### Add code to configure and start the flow server

In the file that's run by your `start` script, add a call to `startFlowServer`.
This method will start an Express server set up to serve your flows as web
endpoints.

When you make the call, specify the flows you want to serve:

```ts
ai.startFlowServer({
  flows: [menuSuggestionFlow],
});
```

There are also some optional parameters you can specify:

- `port`: the network port to listen on. If unspecified, the server listens on
  the port defined in the PORT environment variable, and if PORT is not set,
  defaults to 3400.
- `cors`: the flow server's
  [CORS policy](https://www.npmjs.com/package/cors#configuration-options).
  If you will be accessing these endpoints from a web application, you likely
  need to specify this.
- `pathPrefix`: an optional path prefix to add before your flow endpoints.
- `jsonParserOptions`: options to pass to Express's
  [JSON body parser](https://www.npmjs.com/package/body-parser#bodyparserjsonoptions)

### Optional: Define an authorization policy

All deployed flows should require some form of authorization; otherwise, your potentially-expensive generative AI flows would be invocable by anyone.

When you deploy your flows with Cloud Run, you have two options for
authorization:

- **Cloud IAM-based authorization**: Use Google Cloud's native access management
  facilities to gate access to your endpoints. See
  [Authentication](https://cloud.google.com/run/docs/authenticating/overview)
  in the Cloud Run docs for information on providing these credentials.

- **Authorization policy defined in code**: Use the authorization policy feature
  of Genkit flows to verify authorization info using custom code. This is often,
  but not necessarily, token-based authorization.

If you want to define an authorization policy in code, use the `authPolicy`
parameter in the flow definition:

```ts
const myFlow = ai.defineFlow(
  {
    name: "myFlow",
    authPolicy: (auth, input) => {
      if (!auth) {
        throw new Error("Authorization required.");
      }
      // Custom checks go here...
    },
  },
  async () => {
    // ...
  }
);
```

The `auth` parameter of the authorization policy comes from the `auth` property
of the request object. You typically set this property using Express middleware.
See
[Authorization and integrity](/docs/genkit/auth#non-firebase_http_authorization).

### Make API credentials available to deployed flows 

Once deployed, your flows need some way to authenticate with any remote services
they rely on. Most flows will at a minimum need credentials for accessing the
model API service they use.

For this example, do one of the following, depending on the model provider you
chose:

- {Gemini (Google AI)}

  1.  Make sure Google AI is
      [available in your region](https://ai.google.dev/available_regions).

  1.  [Generate an API key](https://aistudio.google.com/app/apikey) for the
      Gemini API using Google AI Studio.

  1.  Make the API key available in the Cloud Run environment:

      1.  In the Cloud console, enable the
          [Secret Manager API](https://console.cloud.google.com/apis/library/secretmanager.googleapis.com?project=_).
      1.  On the [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=_)
          page, create a new secret containing your API key.
      1.  After you create the secret, on the same page, grant your default
          compute service account access to the secret with the **Secret
          Manager Secret Accessor** role. (You can look up the name of the
          default compute service account on the IAM page.)

      In a later step, when you deploy your service, you will need to
      reference the name of this secret.

- {Gemini (Vertex AI)}

  1.  In the Cloud console,
      [Enable the Vertex AI API](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=_)
      for your project.

  1.  On the [IAM](https://console.cloud.google.com/iam-admin/iam?project=_)
      page, ensure that the **Default compute service account** is granted the
      **Vertex AI User** role.

The only secret you need to set up for this tutorial is for the model provider,
but in general, you must do something similar for each service your flow uses.

## 3. Deploy flows to Cloud Run

After you've prepared your project for deployment, you can deploy it using the
`gcloud` tool.

- {Gemini (Google AI)}

  ```posix-terminal
  gcloud run deploy --update-secrets=GOOGLE_GENAI_API_KEY=<your-secret-name>:latest
  ```

- {Gemini (Vertex AI)}

  ```posix-terminal
  gcloud run deploy
  ```

The deployment tool will prompt you for any information it requires.

When asked if you want to allow unauthenticated invocations:

- Answer `Y` if you're not using IAM and have instead defined an authorization
  policy in code.
- Answer `N` to configure your service to require IAM credentials.

## Optional: Try the deployed flow

After deployment finishes, the tool will print the service URL. You can test
it with `curl`:

```posix-terminal
curl -X POST https://<service-url>/menuSuggestionFlow \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" -d '{"data": "banana"}'
```
