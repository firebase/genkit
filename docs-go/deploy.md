# Deploy flows to any app hosting platform

You can deploy Genkit flows as web services using any service that can
host a Go binary.
This page, as an example, walks you through the general process of deploying the
default sample flow, and points out where you must take provider-specific
actions.

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

    If your provider requires you to listen on a specific port, be sure to
    configure Genkit accordingly.

1.  Implement some form of authentication and authorization to gate access to
    the flows you plan to deploy.

    Because most generative AI services are metered, you most likely do not want
    to allow open access to any endpoints that call them. Some hosting services
    provide an authentication layer as a frontend to apps deployed on them,
    which you can use for this purpose.

1.  Make API credentials available to your deployed function. Do one of the
    following, depending on the model provider you chose:

    - {Gemini (Google AI)}

      1.  Make sure Google AI is
          [available in your region](https://ai.google.dev/available_regions).

      1.  [Generate an API key](https://aistudio.google.com/app/apikey) for the
          Gemini API using Google AI Studio.

      1.  Make the API key available in the deployed environment.

          Most app hosts provide some system for securely handling secrets such
          as API keys. Often, these secrets are available to your app in the
          form of environment variables. If you can assign your API key to the
          `GOOGLE_GENAI_API_KEY` variable, Genkit will use it automatically.
          Otherwise, you need to modify the `googleai.Init()` call to explicitly
          set the key. (But don't embed the key directly in code! Use the secret
          management facilities provided by your hosting provider.)

    - {Gemini (Vertex AI)}

      1.  In the Cloud console,
          [Enable the Vertex AI API](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=_)
          for your project.

      1.  On the [IAM](https://console.cloud.google.com/iam-admin/iam?project=_)
          page, create a service account for accessing the Vertex AI API if you
          don't alreacy have one.

          Grant the account the **Vertex AI User** role.

      1.  [Set up Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc#on-prem)
          in your hosting environment.

      1.  Configure the plugin with your Google Cloud project ID and the Vertex
          AI API location you want to use. You can do so either by setting the
          `GCLOUD_PROJECT` and `GCLOUD_LOCATION` environment variables in your
          hosting environment, or in your `vertexai.Init()` call.

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
    flow using your provider's tools.
