# Chat with a PDF file

This codelab shows you how to use Genkit to implement an app that lets you
chat with a PDF file.

## Prerequisites

This codelab assumes that you’re familiar with building applications with
Node.js. To complete this codelab, make sure that your development environment
meets the following requirements:

- Node.js v20+
- npm

## Create a new project

1. Create a new empty folder.

   ```shell
   mkdir chat-with-a-pdf
   cd chat-with-a-pdf
   ```

1. Initialize a new TypeScript project.

   ```shell
   npm init -y
   ```


## Install Genkit

Install the following Genkit dependencies to use Genkit in your project:

- `genkit` provides Genkit core capabilities.
- `@genkit-ai/googleai` provides access to the Google AI Gemini models.

```shell
npm install genkit @genkit-ai/googleai
```

## Configure your model API key

For this guide, we’ll show you how to use the Gemini API, which provides a
generous free-of-charge tier and does not require a credit card to get 
started. To use the Gemini API, you'll need an API key. If you don't 
already have one, create a key in Google AI Studio.

[Get an API key from Google AI Studio](https://makersuite.google.com/app/apikey)

After you’ve created an API key, set the `GOOGLE_GENAI_API_KEY` environment
variable to your key with the following command:

```shell
export GOOGLE_GENAI_API_KEY=<your API key>
```

> **Note:** While this tutorial uses the Gemini API from AI Studio, Genkit
supports a wide variety of model providers, including:
> * [Gemini from Vertex AI](https://firebase.google.com/docs/genkit/plugins/vertex-ai#generative_ai_models)
> * Anthropic’s Claude 3 models and Llama 3.1 through the [Vertex AI Model Garden](https://firebase.google.com/docs/genkit/plugins/vertex-ai#anthropic_claude_3_on_vertex_ai_model_garden)
> * Open source models through [Ollama](https://firebase.google.com/docs/genkit/plugins/ollama)
> * [Community-supported providers](https://firebase.google.com/docs/genkit/models#models-supported) such as OpenAI and Cohere.

## Import and initialise Genkit

1. Create a new folder `src`, and inside it, a new file `index.ts`. Add the
following lines to import Genkit and the Google AI plugin.

   ```typescript
   import {gemini15Flash, googleAI} from '@genkit-ai/googleai';
   import {genkit} from 'genkit';
   ```

1. Add the following lines to configure Genkit and set Gemini 1.5 Flash as the
default model.

   ```typescript
   const ai = genkit({
     plugins: [googleAI()],
     model: gemini15Flash,
   });
   ```

1. Add the main body of your app.

   ```typescript
   (async () => {
     try {
       // 1: get command line arguments
       // 2: load PDF file
       // 3: construct prompt
       // 4: start chat
       // 5: chat loop
     } catch (error) {
       console.error("Error parsing PDF or interacting with Genkit:", error);
     }
   })(); // <-- don't forget the trailing parentheses to call the function!
   ```

## Load and parse a PDF file

In this step, you will write code to load and parse a PDF file.

1. Install `pdf-parse`.

   ```typescript
   npm i pdf-parse
   ```

1. Import the PDF library into your app.

   ```typescript
   import pdf from 'pdf-parse';
   import fs from 'fs';
   ```

1. Read the PDF filename that was passed in from the command line.

   ```typescript
     // 1: get command line arguments
     const filename = process.argv[2];
     if (!filename) {
       console.error("Please provide a filename as a command line argument.");
       process.exit(1);
     }
   ```

1. Load the contents of the PDF file.

   ```typescript
     // 2: load PDF file
     let dataBuffer = fs.readFileSync(filename);
     const { text } = await pdf(dataBuffer);
   ```

## Set up the prompt

Follow these steps to set up the prompt.

1. Allow the user to provide a custom prompt via the command line. If they don’t
provide a prompt, use a default.

   ```typescript
   const prefix = process.argv[3] || "Answer the user's questions about the contents of this PDF file.";
   ```

1. Inject the prompt prefix and the full text of the PDF file into the prompt for
the model.

   ```typescript
       const prompt = `
         ${prefix}
         Context:
         ${data.text}
       `
   ```

## Implement the chat loop

1. Start the chat with the model by calling the `chat` method, passing the prompt
(which includes the full text of the PDF file).

   ```typescript
   const chat = ai.chat({ system: prompt })
   ```

1. Import `createInterface`; this will allow you to build a text-based UI.

   ```typescript
   import {createInterface} from "node:readline/promises";
   ```

1. Instantiate a text input, then display a message to the user.

   ```typescript
       const readline = createInterface(process.stdin, process.stdout);
       console.log("You're chatting with Gemini. Ctrl-C to quit.\n");
   ```

1. Read the user’s input, then send it to the model using `chat.send`. This part 
of the app will loop until the user presses _CTRL + C_.

   ```typescript
       while (true) {
         const userInput = await readline.question("> ");
         const {text} = await chat.send(userInput);
         console.log(text);
       }
   ```

## Run the app

You can now run the app from your terminal. Open the terminal in the root
folder of your project, then run the following command:

```typescript
npx tsx src/index.ts path/to/some.pdf
```

You can then start chatting with the PDF file.
