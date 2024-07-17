![Firebase Genkit logo](docs/resources/genkit-logo-dark.png#gh-dark-mode-only 'Firebase Genkit')
![Firebase Genkit logo](docs/resources/genkit-logo.png#gh-light-mode-only 'Firebase Genkit')

Firebase Genkit is a framework for building and refining AI-powered applications. It provides open source libraries for Node.js and Go, plus integrated devtools to support developing with AI.

## Who should use Genkit?

Genkit is built for developers adding generative AI to their apps with Node.js or Go, and can run anywhere these runtimes are supported. It works with any generative model API or vector database, and has pre-built implementations through [plugins](#plugin-ecosystem).

While built by [Firebase](https://firebase.google.com), Genkit doesn't require using Firebase or Google Cloud.

## Why use Genkit?

Building AI-powered apps is complex. You need to manage and optimize model configurations, prompts, vector databases, and more, each with their own quirks. The non-deterministic nature of generative models also makes refining your app for production a challenge.

Genkit simplifies this process. Our libraries provide simple abstractions and consistent APIs, making it easy to combine AI building blocks into cohesive workflows. Plus, Genkit's devtools help you efficiently test, debug, and iterate on your AI app.

## Get started

- [Node.js quickstart](https://firebase.google.com/docs/genkit/get-started)
- [Next.js quickstart](hhttps://firebase.google.com/docs/genkit/nextjs)
- [Go quickstart](https://firebase.google.com/docs/genkit-go/get-started-go)

> [!NOTE]
> Genkit for Go is in alpha, so we only recommend using it for prototyping.

## Framework key features

- **Unified generation API:** Generate text, media, structured objects, and tool calls from any generative model using a single, adaptable API.

- **Vector database support:** Add retrieval-augmented generation (RAG) to your apps with simple indexing and retrieval APIs that work across vector database providers.

- **Enhanced prompt engineering:** Define rich prompt templates, model configurations, input/output schemas, and tools all within a single, runnable [.prompt](https://firebase.google.com/docs/genkit/dotprompt) file.

- **AI [work]flows:** Organize your AI app logic into [Flows](https://firebase.google.com/docs/genkit/flows) - functions designed for observability, streaming, integration with Genkit devtools, and easy deployment as API endpoints.

- **Built-in streaming:** Stream content from your Genkit API endpoints to your client app to create snappy user experiences.

## Devtools

Genkit provides a dedicated CLI and UI that help you get started quickly and rapidly iterate on your AI app.

### CLI

The Genkit CLI is the fastest way to initialize a Genkit app and comes with commands to help you run and evaluate Genkit functions, called flows. 

**Install the CLI:** `npm i -g genkit`

**Initialize a Genkit app:** `genkit init`

### Genkit Studio

The Genkit Developer UI helps you rapidly test, debug, and iterate on your AI app using a rich web interface. Key features include:

- **Run:** Invoke and iterate on Genkit flows, prompts, queries, and more in dedicated playgrounds for Genkit components.
- **Inspect:** View detailed traces for previous executions of flows and components, including step-by-step views of complex flows.
- **Evaluate:** See the results of evaluations run on flows against test sets, including scored metrics and links to the traces for evaluation runs. 

<img src="docs/resources/readme-ui-traces-screenshot.png" width="700" alt="Screenshot of Genkit Developer UI showing traces">

## Plugin ecosystem

Access models, vector stores, evaluators, and platform integrations from specific providers like, Google and OpenAI, through Genkit plugins. Plugins are built by the Genkit team, partners, and the community.

- [Genkit Node.js plugins](https://www.npmjs.com/search?q=keywords:genkit-plugin)
- [Genkit Go plugins](https://pkg.go.dev/github.com/firebase/genkit/go#section-directories)

You can contribute to the Genkit ecosystem by:
- [Writing Node.js plugins](https://firebase.google.com/docs/genkit/plugin-authoring)
- Writing Go plugins (docs in progress)

Great examples of community-built plugins for OpenAI, Anthropic, Cohere, and more can be found in this [repository](https://github.com/TheFireCo/genkit-plugins).

## Try Genkit on IDX

<img src="docs/resources/idx-logo.png" width="50" alt="Project IDX logo">

Interested in trying Genkit without needing to set up a local environment? [Try it out on Project IDX](https://idx.google.com/new/genkit), Google's AI-assisted workspace for full-stack app development.

## Community

Join the [Genkit community on Discord](https://discord.gg/qXt5zzQKpc) to keep up with the latest announcements, ask questions, participate in discussions, and showcase any apps or content you've built with Genkit.

Please use our GitHub [issue tracker](https://github.com/firebase/genkit/issues) to file feedback and feature requests.

You can also start and engage in discussions on the [GitHub Discussion](https://github.com/firebase/genkit/discussions) forums.

## Contributing

Genkit is an open source framework, and we welcome contributions. Information on how to get started can be found in our [Contribution Guide](CONTRIBUTING.md).

## Authors

Genkit is built by [Firebase](https://firebase.google.com/products/genkit) with contributions from the [Open Source Community](https://github.com/firebase/genkit/graphs/contributors).