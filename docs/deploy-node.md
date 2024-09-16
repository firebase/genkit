# Deploy flows to any Node.js platform

Firebase Genkit has built-in integrations that help you deploy your flows to
Cloud Functions for Firebase and Google Cloud Run, but you can also deploy your
flows to any platform that can serve an Express.js app, whether it’s a cloud
service or self-hosted.

This page, as an example, walks you through the process of deploying the default
sample flow.

1.  Install the required tools:

    - Make sure you are using node version 20 or higher (run `node --version` to
      check).

1.  Create a directory for the Genkit sample project:

    ```posix-terminal
    export GENKIT_PROJECT_HOME=~/tmp/genkit-express-project

    mkdir -p $GENKIT_PROJECT_HOME

    cd $GENKIT_PROJECT_HOME
    ```

    If you're going to use an IDE, open it to this directory.

1.  Initialize a nodejs project:

    ```posix-terminal
    npm init -y
    ```

1.  Initialize a Genkit project:

    ```posix-terminal
    genkit init
    ```

    1. Select your model:

       - {Gemini (Google AI)}

         The simplest way to get started is with Google AI Gemini API. Make sure
         it's
         [available in your region](https://ai.google.dev/available_regions).

         [Generate an API key](https://aistudio.google.com/app/apikey) for the
         Gemini API using Google AI Studio. Then, set the `GOOGLE_API_KEY`
         environment variable to your key:

         ```posix-terminal
         export GOOGLE_API_KEY=<your API key>
         ```

       - {Gemini (Vertex AI)}

         If the Google AI Gemini API is not available in your region, consider
         using the Vertex AI API which also offers Gemini and other models. You
         will need to have a billing-enabled Google Cloud project, enable AI
         Platform API, and set some additional environment variables:

         ```posix-terminal
         gcloud services enable aiplatform.googleapis.com

         export GCLOUD_PROJECT=<your project ID>

         export GCLOUD_LOCATION=us-central1
         ```

         See https://cloud.google.com/vertex-ai/generative-ai/pricing for Vertex AI pricing.

    1. Choose default answers to the rest of the questions, which will
       initialize your project folder with some sample code.

1.  Build and run the sample code:

    ```posix-terminal
    npm run build

    genkit flow:run menuSuggestionFlow "\"banana\"" -s
    ```

1.  **Optional**: Start the developer UI:

    ```posix-terminal
    genkit start
    ```

    Then, navigate to [http://localhost:4000/flows](http://localhost:4000/flows) and run
    the flow using the developer UI.

    When you're done, press Ctrl+C in the console to quit the UI.

1.  Try out the Express endpoint:

    ```posix-terminal
    npm run start
    ```

    Then, in another window:

    ```posix-terminal
    curl -X POST "http://127.0.0.1:3400/menuSuggestionFlow?stream=true" -H "Content-Type: application/json"  -d '{"data": "banana"}'
    ```

1.  If everything's working as expected, you can deploy the flow to the provider
    of your choice. Details will depend on the provider, but generally, you need
    to configure the following settings:

    | Setting               | Value                                                               |
    | --------------------- | ------------------------------------------------------------------- |
    | Runtime               | Node.js 20 or newer                                                 |
    | Build command         | `npm run build`                                                     |
    | Start command         | `npm run start`                                                     |
    | Environment variables | `GOOGLE_API_KEY=<your-api-key>` (or whichever secrets are required) |
