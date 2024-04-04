# Deploy flows to any Node.js platform

Genkit has built-in integrations that help you deploy your flows to Firebase
Cloud Functions and Google Cloud Run, but you can also deploy your flows to any
platform that can serve an Express.js app, whether it’s a cloud
service or self-hosted.

This page, as an example, walks you through the process of deploying the default
sample flow.

1.  Install the required tools:

    - Make sure you are using node version 18 or higher (run `node --version` to
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

1.  Initialize Genkit in your project:

    ```posix-terminal
    genkit init
    ```

    Select `Node.js` as the deployment platform option and (for the purpose of
    this tutorial) OpenAI as the model provider. Choose defaults for the rest of
    the options.

1.  You will need an OpenAI API key from the
    [OpenAI platform](https://platform.openai.com/api-keys) site. After you have
    created it, run the following to set an environment variable with your key:

    ```posix-terminal
    export OPENAI_API_KEY=<your-api-key>
    ```

1.  Build and run the sample code:

    ```posix-terminal
    npm run build

    genkit flow:run jokeFlow "\"banana\"" -s
    ```

1.  **Optional**: Start the dev UI:

    ```posix-terminal
    genkit start
    ```

    To try out the joke flow, navigate to http://localhost:4000/flows and run
    the flow using the Dev UI.

1.  Try out the Express endpoint:

    ```posix-terminal
    npm run start
    ```

    Then, in another window:

    ```posix-terminal
    curl -X POST "http://127.0.0.1:3400/jokeFlow?stream=true" -H "Content-Type: application/json"  -d '{"data": "banana"}'
    ```

1.  If everything's working as expected, you can deploy the flow to the provider
    of your choice. Details will depend on the provider, but generally, you need
    to configure the following settings:

    | Setting               | Value                                                               |
    | --------------------- | ------------------------------------------------------------------- |
    | Runtime               | Node.js 18 or newer                                                 |
    | Build command         | `npm run build`                                                     |
    | Start command         | `npm run start`                                                     |
    | Environment variables | `OPENAI_API_KEY=<your-api-key>` (or whichever secrets are required) |
