
# AI Primitives

AI Primitives are very easy to use GenAI libraries that provide access to various Google and 3P LLMs, vector stores as well as helpful utilities for working with things like prompts and ways to compose llm logic into higher level constructs.

AI primitives and composition framework are fully instrumented for observability and come with tooling integrations provided via Genkit CLI and Dev UI.

## LLMs

When working with LLMs in Genkit you first need to configure"the model you want to work with. Model configuration is performed via the plugin system. In this example we are configuring VertexAI plugin which provides gemini models (refer to plugin documentation to see which models it provides).

```
configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    vertexAI({ projectId: getProjectId(), location: getLocation() || 'us-central1' }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'info',
});
```

Also note that different pluging and model use different methods of authentication. For example, Vertex API uses [Google Auth Library](https://cloud.google.com/nodejs/docs/reference/google-auth-library/latest) so it can pull required credentials using [Application Default Credentials](https://cloud.google.com/nodejs/docs/reference/google-auth-library/latest#application-default-credentials). To configure a "text" model you just need to run: 


To use models provided by the plugin you can either refer to them by name (e.g. `'vertex-ai/gemini-1.0-pro'`) or some plugins export model ref objects which provide additional type info about the model capabilities and options.

```javascript
import { geminiPro } from '@google-genkit/plugin-vertex-ai';
```

### `generate` function

`generate` is a helper function for working with text models.

To simply call the model:

```javascript
import { generate } from '@google-genkit/ai/generate';
import { geminiPro } from '@google-genkit/plugin-vertex-ai';

const llmResponse = await generate({
  model: geminiPro,
  prompt: "Tell me a joke."
});

console.log(await llmResponse.text());
```

you can pass in various model options for that model, including custom model for specific LLM.

```javascript
const response = await generate({
  model: geminiPro, 
  prompt, 
  config: {
    temperature: 1,
    custom: {
      stopSequences: ["abc"]
    }
  },
});
```

If the model supports multimodal input you can pass in images as input:

```javascript
const geminiProVision = configureVertexAiTextModel({ modelName: "gemini-pro-vision" });

const result = await generate({
  model: geminiProVision,
  prompt: [
    { text: 'describe the following image:' },
    { media: { url: imageUrl, contentType: 'image/jpeg' } },
  ],
});
```

Model can also support tools/function calling:

```javascript
const myTool = action(
  {
    name: "myJoke",
    description: "useful when you need a joke to tell.",
    input: z.object({ subject: z.string() }),
    output: z.string(),
  },
  async (input) => "haha Just kidding no joke! got you"
);

const llmResponse = await generate({
  model: geminiPro, 
  prompt: "Tell me a joke.", 
  tools: [myTool],
  options: {
    temperature: 0.5,
  },  
});
```

This will automatically call the tools in order to fulfill user prompt.

You can specify `returnToolRequests: true` for manual control of tool calling. 

```javascript
const llmResponse = await generate({
  model: geminiPro, 
  prompt: "Tell me a joke.", 
  tools: [myTool],
  returnToolRequests: true,
  options: {
    temperature: 0.5,
  },  
});
```

And you can stream output from models that support it:

```javascript
await generate({
  model: geminiPro,
  prompt: "Tell me a very long joke.",
  streamingCallback: (chunk) => {
    console.log(chunk)
  }
});
```

## Prompts

Genkit comes with a prompt library called dotprompt.

The library allows you to define prompt in a separate file:

```
---
model: google-ai/gemini-pro
output:
  schema:
    type: object
    properties:
      title: {type: string, description: "recipe title"}
      ingredients: 
        type: array
        items: {type: object, properties: {name: {type: string}, quantity: {type: string}}}
      steps: {type: array, items: {type: string}}
---

You are a chef famous for making creative recipes that can be prepared in 45 minutes or less.

Generate a recipe for {{food}}.
```


```
import { prompt } from '@google-genkit/dotprompt';

const food = 'mexican asian fusion';
const recipePrompt = await prompt('recipe');

const result = await recipePrompt.generate({
  variables: { food },
});

console.log(result.output());
```

## Retrievers

Retriever is a concept which encapsulates logic relates to any kind of document
retrieval for, for example, RAG use cases. The most popular retrieval cases
typically include retrieval from vector stores.

To create a retriever you can use one of the provided implementations or easily
create your own.

Let's take a look at a simple/naive file-based vector similarity retriever that
the Genkit team provides out-of-the box for simple prototyping (DO NOT USE IN
PRODUCTION, retrievers for Chroma and Pinecone are provided without support for
ingestion, more WIP).

```javascript
import {
  configureNaiveFilestoreRetriever,
  importDocumentsToNaiveFilestore,
} from "@google-genkit/providers/vectorstores";
import { configureVertexTextEmbedder } from "@google-genkit/providers/embedders";

const vertexEmbedder = configureVertexTextEmbedder({
  projectId: getProjectId(),
  modelName: "textembedding-gecko@001",
});
const spongebobFacts = configureNaiveFilestoreRetriever({
  embedder: vertexEmbedder,
  embedderOptions: {
    temperature: 0,
    topP: 0,
    topK: 1,
  },
});
```

Note that you also need an embedder (embeddings model) to generate embeddings
vectors.

You can then import documents into the store.

```javascript
const docs = [
  {
    content: "SpongeBob's primary job is working as the fry cook at the Krusty Krab.",
    metadata: { type: "tv", show: "Spongebob" },
  },
  {
    content: "SpongeBob is a yellow sea sponge.",
    metadata: { type: "tv", show: "Spongebob" },
  },
]

// Importing docs is only currently supported in the Naive Filestore. If you
// are using Chroma/Pinecone, you should ingest documents using the
// corresponding native SDKs. This is WIP.
importDocumentsToNaiveFilestore({
  docs: docs,
  embedder: vertexEmbedder,
  embedderOptions: {
    temperature: 0,
    topP: 0,
    topK: 1,
  },
});
```

you can then use the provided `retrieve` function to retrieve documents from
the store:

```javascript
const docs = await retrieve({
  dataStore: spongebobFacts,
  query: "Who is spongebob?",
  options: { k: 3 }
});
```

It's also very easy to create your own retriever. This is useful if your
documents are managed in a document store that is not currently supported in
Genkit (eg: MySQL, Google Drive, etc.). The Genkit SDK provides a flexible
`retrieverFactory` method that lets you provide custom code to fetch documents.
You can also define custom retrievers that build on top of existing retrievers
in Genkit and apply advanced RAG techniques (ex. reranking or prompt
extensions) on top.


```javascript
import {
  CommonRetrieverOptionsSchema,
  retrieverFactory,
  TextDocumentSchema,
  type TextDocument,
} from "@google-genkit/ai/retrievers";

const MyAdvancedOptionsSchema = CommonRetrieverOptionsSchema.extend({
  preRerankK: z.number().max(1000),
});

const advancedRetriever = retrieverFactory(
  "custom",
  "advancedRag",
  z.string(),
  TextDocumentSchema,
  MyAdvancedOptionsSchema,
  async (input, options) => {
    const extendedPrompt = await extendPrompt(input);
    const docs = await retrieve({
      dataStore: spongebobFacts,
      query: extendedPrompt,
      options: { k: options.preRerankK || 10 }
    });
    const rerankedDocs = await rerank(docs);
    return rerankedDocs.slice(0, options.k || 3);
  }
);
```

(`extendPrompt` and `rerank` is something you would have to implement yourself, currently not provided by the framework)

And then you can just swap out your retriever:

```javascript
const docs = await retrieve({
  dataStore: advancedRetriever,
  query: "Who is spongebob?",
  options: { preRerankK: 7, k: 3 }
});
```