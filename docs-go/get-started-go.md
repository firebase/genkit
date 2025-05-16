# Get started with Genkit using Go (alpha)

The Genkit libraries for Go are now available for preview! Because the
Go libraries are currently in Alpha, you might see API and functional changes as
development progresses. We recommend using it only for prototyping and
exploration.

If you discover issues with the libraries or this documentation please report
them in our [GitHub repository](https://github.com/firebase/genkit/).

To get started with Genkit, install the Genkit CLI and run
`genkit init` in a Go project. The rest of this page shows you how.

## Requirements

- Go 1.22 or later. See [Download and install](https://go.dev/doc/install) in
  the official Go docs.

- Node.js 20 or later (for the Genkit CLI and UI). See the next section for a
  brief guide on installing Node.

## Install Genkit {:#install}

1.  If you don't already have Node 20 or newer on your system, install it now.

    Recommendation: The [`nvm`](https://github.com/nvm-sh/nvm) and
    [`nvm-windows`](https://github.com/coreybutler/nvm-windows) tools are a
    convenient way to install specific versions of Node if it's not already
    installed on your system. These tools install Node on a per-user basis, so you
    don't need to make system-wide changes.

    To install `nvm`:

    - {Linux, macOS, etc.}

      Run the following command:

      ```posix-terminal
      curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
      ```

    - {Windows}

      Download and run the installer as described in the [nvm-windows docs](https://github.com/coreybutler/nvm-windows?tab=readme-ov-file#install-nvm-windows).

    Then, to install Node and `npm`, open a new shell and run the following
    command:

    ```posix-terminal
    nvm install 20
    ```

1.  Install the Genkit CLI by running the following command:

    ```posix-terminal
    npm i -g genkit-cli
    ```

    This command installs the Genkit CLI into your Node installation directory
    so that it can be used outside of a Node project.

## Create and explore a sample project {:#explore}

1.  Create a new project directory:

    ```posix-terminal
    mkdir genkit-intro && cd genkit-intro
    ```

1.  Initialize a Genkit project:

    ```posix-terminal
    genkit init
    ```

    1. Select `Go` as the runtime environment.

    1. Select your model:

       - {Gemini (Google AI)}

         The simplest way to get started is with Google AI Gemini API. Make sure
         it's
         [available in your region](https://ai.google.dev/available_regions).

         [Generate an API key](https://aistudio.google.com/app/apikey) for the
         Gemini API using Google AI Studio. Then, set the `GOOGLE_GENAI_API_KEY`
         environment variable to your key:

         ```posix-terminal
         export GOOGLE_GENAI_API_KEY=<your API key>
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

         See [Vertex AI pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing).

    1. Specify anything for the module name. For example: `example/genkit-intro`

    1. Choose default answers to the rest of the questions, which will
       initialize your project folder with some sample code.

    The `genkit init` command creates a sample Go module and installs the
    required dependencies. The file `main.go` contains a single flow,
    `menuSuggestionFlow`, that prompts an LLM to suggest an item for a
    restaurant with a given theme.

    This file looks something like the following (the plugin configuration steps
    might look different if you selected Vertex AI):

    ```golang
    {% includecode github_path="firebase/genkit/go/internal/doc-snippets/init/main.go" region_tag="main" adjust_indentation="auto" %}
    ```

    As you build out your app's AI features with Genkit, you will likely create
    flows with multiple steps such as input preprocessing, more sophisticated
    prompt construction, integrating external information sources for
    retrieval-augmented generation (RAG), and more.

1.  Now you can run and explore Genkit features and the sample project locally
    on your machine. Download and start the Genkit Developer UI:

    ```posix-terminal
    genkit start
    ```

    <img src="resources/welcome_to_genkit_developer_ui.png" alt="Welcome to
    Genkit Developer UI" class="screenshot attempt-right">

    The Genkit Developer UI is now running on your machine. When you run models
    or flows in the next step, your machine will perform the orchestration tasks
    needed to get the steps of your flow working together; calls to external
    services such as the Gemini API will continue to be made against live
    servers.

    Also, because you are in a dev environment, Genkit will store traces and
    flow state in local files.

1.  The Genkit Developer UI downloads and opens automatically when you run the
    `genkit start` command.

    The Developer UI lets you see which flows you have defined and models you
    configured, run them, and examine traces of previous runs. Try out some of
    these features:

    - On the **Run** tab, you will see a list of all of the flows that you have
      defined and any models that have been configured by plugins.

      Click **menuSuggestionFlow** and try running it with some input text (for
      example, `"cat"`). If all goes well, you'll be rewarded with a menu
      suggestion for a cat themed restaurant.

    - On the **Inspect** tab, you'll see a history of flow executions. For each
      flow, you can see the parameters that were passed to the flow and a trace
      of each step as they ran.
