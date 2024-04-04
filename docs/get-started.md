# Get started

Genkit has built-in support for several language models, both local and
cloud-based. In this guide, you will use the Gemini Pro model, provided by the
Gemini API.

If you want to follow along with this introduction, you need Node.js 18 or
later.

1.  Install Genkit CLI by running

    ```posix-terminal
    npm i -g genkit
    ```

1.  Create a new project folder and install Genkit CLI:

    ```posix-terminal
    mkdir genkit-intro && cd genkit-intro

    npm init -y
    ```

1.  Initialize a Genkit project:

    ```posix-terminal
    genkit init
    ```

    1. Select `googleCloud` as the deployment platform option (you don't need a Google Cloud project to get started).

    1. Select your model:

       The simplest way to get started is with Google AI Gemini API. Make sure it's available in your region: https://ai.google.dev/available_regions

       [Generate an API key](https://aistudio.google.com/app/apikey) for the
       Gemini API using Google AI Studio. Then, set the `GOOGLE_API_KEY`
       environment variable to your key:

       ```posix-terminal
       export GOOGLE_API_KEY=<your API key>
       ```

       If the Google AI Gemini API is not available in your region, consider using the Vertex AI API which also offers Gemini and other models. You will need to have a billing-enabled Google Cloud project, enable AI Platform API, and set some additional environment variable:

       ```posix-terminal
       gcloud services enable aiplatform.googleapis.com

       export GCLOUD_PROJECT=<your project ID>
       export GCLOUD_LOCATION=us-central1
       ```

       See https://cloud.google.com/vertex-ai/generative-ai/pricing for Vertex AI pricing.

       If you are an existing OpenAI user there's also an option to use OpenAI models.

    1. Choose default answers to the rest of the questions, which will initialize your project folder with some sample code.

1.  Edit package.json and make sure the `main` field is set to `lib/index.js`.

1.  Now you can run and explore Genkit features and sample project locally on your machine. Start the Genkit Developer UI:

    ```posix-terminal
    genkit start
    ```

    The Genkit Developer UI is now running on your machine. When you run models or flows
    in the next step, your machine will perform the orchestration tasks needed
    to get the steps of your flow working together; calls to external services
    such as the Gemini API will continue to be made against live servers.

    Also, because you are in a dev environment, Genkit will store traces and
    flow state in local files.

1.  Open the Genkit Developer UI by clicking the link printed by the
    `genkit start` command.

    The Developer UI lets you see which flows you have defined and models you
    configured, run them, and examine traces of previous runs. Try out some of
    these features:

    - On the "Run" tab, you will see a list of all of the flows tat you have
      defined and any models that have been configured by plugins.

      Click **jokeFlow** and try running it with some input text (for example,
      `"manatees"`). If all goes well, you'll be rewarded with a joke about
      manatees. Run it a few more times and you might get one that's funny.

    - On the "Inspect" tab, you'll see a history of flow executions. For each
      flow, you can see the parameters that were passed to the flow and a
      trace of each step as they ran.

Next steps: check out how to build and deploy your Genkit app with [Firebase](firebase.md) and [Cloud Run](cloud-run.md).
