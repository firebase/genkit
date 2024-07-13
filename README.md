![Firebase Genkit logo](docs/resources/genkit-logo-dark.png#gh-dark-mode-only 'Firebase Genkit')
![Firebase Genkit logo](docs/resources/genkit-logo.png#gh-light-mode-only 'Firebase Genkit')

Firebase Genkit is a framework for TypeScript and Go, designed to help you build and iterate on AI-powered applications and features.

## Who is Genkit for?

Genkit is for any developer who wants to integrate generative AI capabilities into their apps using TypeScript or Go. Code written with Genkit libraries can be deployed anywhere that supports Node.js and Go runtimes.

Genkit is built by Firebase, Google's app development platform, but does not require you to be a Firebase or Google Cloud user.

## Why use Genkit?

Integrating generative AI into apps is complicated. You may need to tie together many components and APIs like gen AI models (LLMs), prompts, vector stores, embedders, and tools - each with provider-specific implementations and quirks. Once you've built a simple prototype, refining it to production quality can be a difficult process due to the non-deterministic nature of gen AI models.

If you're a developer who's used to building apps and services, learning to work with generative AI models can be intimidating! There's a lot to learn 

Genkit helps building apps with generative AI APIs by idiomatic patterns, observability, type-safety, integrated tooling, and lighweight, composable abstractions.

> [!NOTE]
> Genkit for Go is currently in Alpha, so we only recommend using it for prototyping and exploration. 

Review the [documentation](https://firebase.google.com/docs/genkit) for details and samples.

## Key features

### GenAI models

**Unified API for generation** across AI models built by Google (Gemini, Gemma) and third party providers. Supports multimodal input, multimedia content generation, and custom options.

**Generate structured output** as strongly-typed objects with custom schemas for easy integration into your app.

**Define custom tools for your AI models** to fetch data, display UI, write to a database, and more.

**Write well structured prompts** with all relevant metadata encapsulated in a single [dotprompt](https://firebase.google.com/docs/genkit/dotprompt) file. Supports handlebars templating, history, multimedia, and more.

![Screenshot of IDE showing Firebase Genkit RAG sample code](docs/resources/readme-rag-screenshot.png)

### Retrieval

**Build context-aware AI features** by indexing your data and dynamically retrieving relevant information from your database. Genkit provides flexible, light-weight abstractions for indexers and retrievers that work with any database provider.

### Evaluation

**Evaluate your end-to-end AI workflow** using a variety of pre-built and custom evaluators. As easy as:

```bash
genkit eval:flow myAiWorkflow --input testQuestions.json
```

### Extensibility with plugins

**Access pre-built components and integrations** for models, vector stores, tools, evaluators, observability, and more through Genkit’s open ecosystem of plugins built by Google and the community. For a list of existing plugins from Google and the community, explore the #genkit-plugin keyword [on npm](https://www.npmjs.com/search?q=keywords:genkit-plugin).

You can also use this extensibility to easily define custom components whenever existing plugins don’t fit your needs.

For more information:

- [Genkit plugins on npm](https://www.npmjs.com/search?q=keywords:genkit-plugin)
- [Writing Genkit plugins](https://firebase.google.com/docs/genkit/plugin-authoring)

### Deployment

**Deploy your AI feature with a single command** through the Firebase or Google Cloud CLI to:

- Cloud Functions for Firebase (Node.js only)
- Firebase App Hosting as a Next.js app (Early preview, Node.js only)
- Google Cloud Run (Node.js or Go)

You can also deploy to any container platform where your chosen runtime is supported.

### Observability and monitoring

Genkit is **fully instrumented with OpenTelemetry** and provides hooks to export telemetry data. Easily log traces and telemetry to Google Cloud using pre-built plugins or set up with a custom provider for full end-to-end observability and monitoring in production.

## Genkit Developer UI

Genkit's developer UI enables developers to prototype, develop, and test their AI features locally, resulting in quick turn-around times, key features include:

Key features:

- **Action Runners:** Sandboxed environments that let developers run Genkit flows and perform other actions like chatting with models, running structured prompts or testing retrievers.
- **Trace Viewer:** View previous executions of flows and actions, including step-by-step views of complex flows.
- **Evaluations:** See the results of running evaluations of flows against test sets, including scored metrics and links to the traces for those evaluation runs. For more information see the [evaluation documentation](https://firebase.google.com/docs/genkit/evaluation).

![Screenshot of IDE showing Firebase Genkit RAG sample code](docs/resources/readme-ui-screenshot.png)

## Google Cloud and Firebase integrations

Genkit works great out-of-the-box with Firebase or Google Cloud projects thanks to official plugins and templates that make it easy to integrate Google Cloud and Firebase services for AI, databases, monitoring, authentication, and deployment. These include:

- [Google Cloud plugin](https://firebase.google.com/docs/genkit/plugins/google-cloud): Export logs, metrics, and traces from your AI-powered feature to Cloud Logging, Cloud Tracing, and Firestore.
- [Firebase plugin](https://firebase.google.com/docs/genkit/plugins/firebase): Integrate with Cloud Functions for Firebase, Firebase Authentication, App Check, Firestore, and more.
- [Google Cloud Vertex AI plugin](https://firebase.google.com/docs/genkit/plugins/vertex-ai): Integrate with Vertex AI models (Gemini, Imagen, …), evaluators, and more.
- [Google AI plugin](https://firebase.google.com/docs/genkit/plugins/google-genai): Integrate with Google AI Gemini APIs.
- [Ollama plugin](https://firebase.google.com/docs/genkit/plugins/ollama): Integrate with Ollama to access popular OSS models like Google’s Gemma.
- [pgvector template](https://firebase.google.com/docs/genkit/templates/pgvector): See our template for integrating with pgvector for CloudSQL and AlloyDB.

## Try it out on IDX

<img src="docs/resources/idx-logo.png" width="50" alt="Project IDX logo">

Interested in trying Genkit? [Try it out on Project IDX](https://idx.google.com/new/genkit), Google's AI-assisted workspace for full-stack app development.

## Contributing

Genkit is an open source framework, and we welcome contributions. Information on how to get started can be found in our [contributor guide](CONTRIBUTING.md).

Please use our GitHub [issue tracker](https://github.com/firebase/genkit/issues) to file feedback and feature requests.

You can also reach out to us using the GitHub [discussion](https://github.com/firebase/genkit/discussions) forums.

Firebase Genkit Team
