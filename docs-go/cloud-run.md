# Genkit with Cloud Run

You can deploy Genkit flows as web services using Cloud Run. This page,
as an example, walks you through the process of deploying the default sample
flow.

1.  Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) if
    you haven't already.

1.  Create a new Google Cloud project using the
    [Cloud console](https://console.cloud.google.com) or choose an existing one.
    The project must be linked to a billing account.

    After you create or choose a project, configure the Google Cloud CLI to use
    it:

    ```posix-terminal
    gcloud auth login

    gcloud init
    ```

1.  Create a directory for the Genkit sample project:

    ```posix-terminal
    mkdir -p ~/tmp/genkit-cloud-project

    cd ~/tmp/genkit-cloud-project
    ```

    If you're going to use an IDE, open it to this directory.

1.  Initialize a Go module in your project directory:

    ```posix-terminal
    go mod init example/cloudrun
    ```

1.  Initialize Genkit in your project:

    ```posix-terminal
    genkit init
    ```

    Select the model provider you want to use.

    Accept the defaults for the remaining prompts. The `genkit` tool will create
    a sample source file to get you started developing your own AI flows.
    For the rest of this tutorial, however, you'll just deploy the sample flow.

1.  Edit the sample file (`main.go` or `genkit.go`) to explicitly specify the
    port the flow server should listen on:

    ```golang
    {% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="init" adjust_indentation="auto" %}
    ```

1.  Make API credentials available to your deployed function. Do one of the
    following, depending on the model provider you chose:

    - {Gemini (Google AI)}

      1.  Make sure Google AI is
          [available in your region](https://ai.google.dev/available_regions).

      1.  [Generate an API key](https://aistudio.google.com/app/apikey) for the
          Gemini API using Google AI Studio.

      1.  Make the API key available in the Cloud Run environment:

          1.  In the Cloud console, enable the
              [Secret Manager API](https://console.cloud.google.com/apis/library/secretmanager.googleapis.com?project=_).
          1.  On the
              [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=_)
              page, create a new secret containing your API key.
          1.  After you create the secret, on the same page, grant your default
              compute service account access to the secret with the
              **Secret Manager Secret Accessor** role. (You can look up the name
              of the default compute service account on the IAM page.)

          In a later step, when you deploy your service, you will need to
          reference the name of this secret.

    - {Gemini (Vertex AI)}

      1.  In the Cloud console,
          [Enable the Vertex AI API](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=_)
          for your project.

      1.  On the [IAM](https://console.cloud.google.com/iam-admin/iam?project=_)
          page, ensure that the **Default compute service account** is granted
          the **Vertex AI User** role.

    The only secret you need to set up for this tutorial is for the model
    provider, but in general, you must do something similar for each service
    your flow uses.

1.  **Optional**: Try your flow in the developer UI:

    1.  Set up your local environment for the model provider you chose:

        - {Gemini (Google AI)}

          ```posix-terminal
          export GOOGLE_GENAI_API_KEY=<your API key>
          ```

        - {Gemini (Vertex AI)}

          ```posix-terminal
          export GCLOUD_PROJECT=<your project ID>

          export GCLOUD_LOCATION=us-central1

          gcloud auth application-default login
          ```

    1.  Start the UI:

        ```posix-terminal
        genkit start
        ```

    1.  In the developer UI (http://localhost:4000/), run the flow:

        1.  Click **menuSuggestionFlow**.

        1.  On the **Input JSON** tab, provide a subject for the model:

            ```json
            "banana"
            ```

        1.  Click **Run**.

1.  If everything's working as expected so far, you can build and deploy the
    flow:

    - {Gemini (Google AI)}

      ```posix-terminal
      gcloud run deploy --port 3400 \
        --update-secrets=GOOGLE_GENAI_API_KEY=<your-secret-name>:latest
      ```

    - {Gemini (Vertex AI)}

      ```posix-terminal
      gcloud run deploy --port 3400 \
        --set-env-vars GCLOUD_PROJECT=<your-gcloud-project> \
        --set-env-vars GCLOUD_LOCATION=us-central1
      ```

      (`GCLOUD_LOCATION` configures the Vertex API region you want to use.)

    Choose `N` when asked if you want to allow unauthenticated invocations.
    Answering `N` will configure your service to require IAM credentials. See
    [Authentication](https://cloud.google.com/run/docs/authenticating/overview)
    in the Cloud Run docs for information on providing these credentials.

After deployment finishes, the tool will print the service URL. You can test
it with `curl`:

```posix-terminal
curl -X POST https://<service-url>/menuSuggestionFlow \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" -d '"banana"'
```
