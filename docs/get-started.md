# Get started

## Run an LLM flow locally

Genkit has built-in support for several language models, both local and
cloud-based. In this guide, you will use the Gemini Pro model, provided by the
Gemini API.

If you want to follow along with this introduction, you need Node.js 18 or
later.

1.  Set up a Node project with TypeScript:
    -   `mkdir genkit-intro && cd genkit-intro`
    -   `npm init -y`
    -   `npm install --save-dev typescript`
    -   `npx tsc --init`

    Although TypeScript is not required, Genkit was built with type safety
    in mind, using TypeScript for compile-time type checking and Zod for
    run-time type checking.

1.  Install Genkit in your project:
    -   Download packages zip file:
        [genkit-dist.zip](https://bit.ly/genkit-dist)
    -   Unzip the file into `genkit-dist` folder in your project folder
    -   Run:
        ```
        npm i --save ./genkit-dist/*.tgz
        ```

1.  Create a file `index.ts` with the following contents:

    ```js
    import { generate } from '@genkit-ai/ai/generate';
    import { configureGenkit } from '@genkit-ai/common/config';
    import { flow } from '@genkit-ai/flow';
    import { geminiPro, googleGenAI } from "@genkit-ai/plugin-google-genai";
    import * as z from 'zod';

    configureGenkit({
      plugins: [googleGenAI()],
      enableTracingAndMetrics: true,
      logLevel: 'debug',
    });

    export const jokeFlow = flow(
      { name: 'jokeFlow', input: z.string(), output: z.string() },
      async (subject) => {
        const llmResponse = await generate({
          model: geminiPro,
          prompt: `Tell a joke about ${subject}.`,
        });
        return llmResponse.text();
      }
    );
    ```

    And compile it:

    ```
    npx tsc
    ```

    This example is a single step flow that calls the Gemini API with a
    simple prompt and returns the result. As you build out your app's AI
    features with Genkit, you will likely create flows with multiple steps such
    as Input preprocessing, more sophisticated prompt construction, integrating
    external information sources for retrieval-augmented generation (RAG),
    waiting for human intervention, and more.

1.  [Generate an API key](https://aistudio.google.com/app/apikey) for the
    Gemini API using Google AI Studio. Then, set the `GOOGLE_API_KEY`
    environment variable to your key:

    ```
    export GOOGLE_API_KEY=<your API key>
    ```

1.  Now you can run and explore your flow locally on your machine. Start
    the Genkit Dev UI:

    ```
    npx genkit start
    ```

    The Genkit Dev UI is now running on your machine. When you run your flow
    in the next step, your machine will perform the orchestration tasks needed
    to get the steps of your flow working together; calls to external services
    such as the Gemini API will continue to be made against live servers.

    Also, because you are in a dev environment, Genkit will store traces and
    flow state in local files.

1.  Open the Genkit Dev UI by clicking the link printed by the `genkit
    start` command.

    This Dev UI lets you see which flows you have defined and models you
    configured, run them, and examine traces of previous runs. Try out some of
    these features:

    -   On the Actions tab you will see a list of all of the flows you have
        defined and any models that have been configured by plugins.

        Click on jokeFlow and try running it with some input text (for example,
        `"manatees"`). If all goes well, you'll be rewarded with a joke about
        manatees. Run it a few more times and you might get one that's funny.

    -   On the Flows tab, you'll see a history of flow executions. For each
        entry you can see the parameters that were passed to the flow and a trace
        of each step as they run.

## Deploy your flow

Now that you have a basic flow running on your machine, try deploying it to a
cloud service where your apps can call it. You can deploy your Genkit flows to
any cloud service that can run Node.js, but in this guide, you'll use Cloud
Functions for Firebase.

If you want to follow along with this section, you need the [Firebase
CLI](https://firebase.google.com/docs/cli#install_the_firebase_cli) and a Google
Cloud billing account.

1.  Create a new project in the Firebase console. In your new project, do
    the following:
    -   Create a Cloud Firestore database.
    -   Upgrade your project to the Blaze plan, which is required to
        deploy Cloud Functions.
1.  Initialize your project:
    -   `mkdir genkit-intro-firebase && cd genkit-intro-firebase`
    -   `firebase init`

    The Firebase CLI will ask you how to configure your project. Choose the
    following settings:

    -   Specify the project you created in the previous step.
    -   Enable the Cloud Firestore and Cloud Functions services.
    -   Accept the default settings for Cloud Firestore.
    -   Select TypeScript as the language for your Cloud Functions; you
        can otherwise accept the defaults.

1.  Edit tsconfig.js and add the following setting to `compilerOptions`:

    ```
    "skipLibCheck": true,
    ```

1.  Install Genkit:
    -   Download
        [packages zip file](https://bit.ly/genkit-dist)
        and unzip into `functions/genkit-dist` folder.
    -   `cd functions`
    -   `npm i --save ./genkit-dist/*.tgz`
    -   `cd ..`

1.  Replace the contents of `src/index.ts` with the following:

    ```js
    import * as z from 'zod';
    import { generate } from '@genkit-ai/ai/generate';
    import { getProjectId } from '@genkit-ai/common';
    import { configureGenkit } from '@genkit-ai/common/config';
    import { firebase } from '@genkit-ai/plugin-firebase';
    import { noAuth, onFlow } from '@genkit-ai/plugin-firebase/functions';
    import { geminiPro, googleGenAI } from "@genkit-ai/plugin-google-genai";
    import { defineSecret } from 'firebase-functions/params';

    const googleaiApiKey = defineSecret('GOOGLE_API_KEY');

    configureGenkit({
      plugins: [
        firebase({ projectId: getProjectId() }),
        googleGenAI()
      ],
      enableTracingAndMetrics: true,
      traceStore: 'firebase',
      logLevel: 'debug',
    });

    export const jokeFlow = onFlow(
      {
        name: 'jokeFlow', input: z.string(), output: z.string(), authPolicy: noAuth(),
        httpsOptions: { secrets: [googleaiApiKey] }
      },
      async (subject) => {
        process.env.GOOGLE_API_KEY = googleaiApiKey.value();

        const llmResponse = await generate({
          model: geminiPro,
          prompt: `Tell a joke about ${subject}.`,
        });
        return llmResponse.text();
      }
    );
    ```

    This is very similar to the code you ran locally in the last section,
    with a few important differences:

    -   It now uses Cloud Firestore to store flow traces.
    -   It now defines your flow using `onFlow` instead of `flow`. `onFlow` Is a
        convenience function provided by the `firebase` plugin that wraps your flow
        in a Cloud Functions HTTP request handler.
    -   It defines an authorization policy, which establishes the authorization       
        requirements required to access your deployed endpoint. This example sets
        the policy to `noAuth()` so you can easily try the endpoint, but
        _never do this in production_.
    -   It now gets the API key using Cloud Secret Manager instead of from an
        environment variable.

1.  Deploy your function:

    ```
    firebase deploy --only functions
    ```

    When prompted, provide your API key for the Gemini API. Make sure this
    key is for the same project into which you are deploying your function.

    After deployment completes, the Firebase CLI will print the URL of the
    endpoint.

1.  Try making a request to your deployed endpoint. For example, using `curl`:

    ```
    curl -m 70 -X POST https://jokeflow-xyz.a.run.app -H "Content-Type: application/json" -d '{"start": {"input": "bananas"}}'
    ```

    If all goes well, you'll get a response like the following:

    ```
    {"name":"e64efa71-a63d-4618-bad7-33e61e4622ad","done":true,
    "result":{"response":"What do you call a banana that's been in the sun too long?\n\nA tanana!"}}
    ```

The getting started guide has walked you through the basics of writing a
generative AI flow, running it locally, and deploying it to a cloud endpoint.
The flows you actually build in your apps will likely be more complex with more
steps per flow. The rest of the docs teach you about the various building
blocks Genkit makes available for you to create such flows.