# Chat with a PDF file

You can use Genkit to build an app that lets its user chat with a PDF file.
To do this, follow these steps:

1. [Set up your project](#setup-project)
1. [Import the required dependencies](#import-dependencies)
1. [Configure Genkit and the default model](#configure-genkit)
1. [Load and parse the PDF file](#load-and-parse)
1. [Set up the prompt](#set-up-the-prompt)
1. [Implement the UI](#implement-the-interface)
1. [Implement the chat loop](#implement-the-chat-loop)
1. [Run the app](#run-the-app)

This guide explains how to perform each of these tasks.

## Dependencies {:#dependencies}

Before starting work, you should have these dependencies set up:

* [Node.js v20+](https://nodejs.org/en/download)
* [npm](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)

## Tasks {:#tasks}

After setting up your dependencies, you can build the
project, itself.

### 1. Set up your project {:#setup-project}

1. Create a directory structure and a file to hold
your source code.

   ```shell
   $ mkdir -p chat-with-a-pdf/src && \
   cd chat-with-a-pdf/src && \
   touch index.ts
   ```

1. Initialize a new TypeScript project.

   ```shell
   $ npm init -y
   ```

1. Install the pdf-parse module:

    ```shell
    $ npm i pdf-parse
    ```

1. Install the following Genkit dependencies to use Genkit in your project:

    ```shell
    $ npm install genkit @genkit-ai/googleai
    ```

* `genkit` provides Genkit core capabilities.
* `@genkit-ai/googleai` provides access to the Google AI Gemini models.

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5. Get and configure
your model API key {:#configure-your-model-api-key}

<ul style="list-style-type:none;">

To use the Gemini API, which this codelab uses, you must first
configure an API key. If you don't already have one,
<a href="https://makersuite.google.com/app/apikey" target="_blank">create a
key</a> in Google AI Studio.

The Gemini API provides a generous free-of-charge tier and does not require a
credit card to get started.

After creating your API key, set the <code>GOOGLE_GENAI_API_KEY`</code>
environment variable to your key with the following command:

<pre class="prettyprint lang-shell">
$ export GOOGLE_GENAI_API_KEY=&lt;your API key&gt;
</pre>

</ul>
<br>

**Note:** Although this tutorial uses the Gemini API from AI Studio, Genkit
supports a wide variety of model providers, including:

* [Gemini from Vertex AI](https://firebase.google.com/docs/genkit/plugins/vertex-ai#generative_ai_models).
* Anthropic's Claude 3 models and Llama 3.1 through the
[Vertex AI Model Garden](https://firebase.google.com/docs/genkit/plugins/vertex-ai#anthropic_claude_3_on_vertex_ai_model_garden),
as well as community plugins.
* Open source models through
[Ollama](https://firebase.google.com/docs/genkit/plugins/ollama).
* [Community-supported providers](https://firebase.google.com/docs/genkit/models#models-supported) such as OpenAI and Cohere.

### 2. Import the required dependencies {:#import-dependencies}

In the `index.ts` file that you created, add the
following lines to import the dependencies required for this project:

   ```typescript
   import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
   import { genkit } from 'genkit';
   import pdf from 'pdf-parse';
   import fs from 'fs';
   import { createInterface } from "node:readline/promises";
   ```
<ul>
  <li>The first two lines import Genkit and the Google AI plugin.</li>
  <li>The second two lines are for the pdf parser.</li>
  <li>The fifth line is for implementing your UI.</li>
</ul>

### 3. Configure Genkit and the default model {:#configure-genkit}

Add the following lines to configure Genkit and set Gemini 1.5 Flash as the
default model.

   ```typescript
   const ai = genkit({
     plugins: [googleAI()],
     model: gemini15Flash,
   });
   ```

You can then add a skeleton for the code and error-handling.

   ```typescript
   (async () => {
     try {
       // Step 1: get command line arguments

       // Step 2: load PDF file

       // Step 3: construct prompt

       // Step 4: start chat

       Step 5: chat loop

     } catch (error) {
       console.error("Error parsing PDF or interacting with Genkit:", error);
     }
   })(); // <-- don't forget the trailing parentheses to call the function!
   ```
### 4. Load and parse the PDF {:#load-and-parse}

1. Under Step 1, add code to read the PDF filename that was passed
in from the command line.

   ```typescript
     const filename = process.argv[2];
     if (!filename) {
       console.error("Please provide a filename as a command line argument.");
       process.exit(1);
     }
   ```

1. Under Step 2, add code to load the contents of the PDF file.

   ```typescript
     let dataBuffer = fs.readFileSync(filename);
     const { text } = await pdf(dataBuffer);
   ```

### 5. Set up the prompt {:#set-up-the-prompt}

Under Step 3, add code to set up the prompt:

   ```typescript
   const prefix = process.argv[3] || "Sample prompt: Answer the user's questions about the contents of this PDF file.";
   const prompt = `
     ${prefix}
     Context:
     ${text}
       `
   ```

* The first `const` declaration defines a default prompt if the user doesn't
pass in one of their own from the command line.
* The second `const` declaration interpolates the prompt prefix and the full
text of the PDF file into the prompt for the model.

### 6. Implement the UI {:#implement-the-interface}

Under Step 4, add the following code to start the chat and
implement the UI:

   ```typescript
   const chat = ai.chat({ system: prompt })
   const readline = createInterface(process.stdin, process.stdout);
   console.log("You're chatting with Gemini. Ctrl-C to quit.\n");
   ```

The first `const` declaration starts the chat with the model by
calling the `chat` method, passing the prompt (which includes
the full text of the PDF file). The rest of the code instantiates
a text input, then displays a message to the user.

### 7. Implement the chat loop {:#implement-the-chat-loop}

Under Step 5, add code to receive user input and
send that input to the model using `chat.send`. This part
of the app loops until the user presses _CTRL + C_.

   ```typescript
       while (true) {
         const userInput = await readline.question("> ");
         const {text} = await chat.send(userInput);
         console.log(text);
       }
   ```

### 8. Run the app {:#run-the-app}

Run the app from your terminal. Open the terminal in the root
folder of your project, then run the following command:

```typescript
npx tsx src/index.ts path/to/some.pdf
```

You can then start chatting with the PDF file.
