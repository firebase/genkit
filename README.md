![Firebase Genkit logo](docs/resources/genkit-logo-dark.png#gh-dark-mode-only 'Firebase Genkit')
![Firebase Genkit logo](docs/resources/genkit-logo.png#gh-light-mode-only 'Firebase Genkit')

Genkit is a framework for building AI-powered applications. It provides open-source libraries for Node.js and Go, along with integrated tools to streamline your development workflow.

## What can you build with Genkit?

Genkit is versatile to support many AI applications. Common use cases include:

- **Intelligent agents:** Create agents that understand user requests and perform tasks autonomously, such as personalized travel planning or itinerary generation.
    - Example: [Compass Travel Planning App](https://developers.google.com/solutions/compass)

- **Data transformation:** Convert unstructured data, like natural language, into structured formats (e.g., objects, SQL queries, tables) for integration into your app or data pipeline.
    - Example: [Add Natural Language AI Data Filters with Genkit](https://medium.com/firebase-developers/how-to-add-natural-language-ai-data-filters-to-your-app-71d64a79624d)

- **Retrieval-augmented generation:** Create apps that provide accurate and contextually relevant responses by grounding generation with your own data sources.
    - Example: [Build AI features powered by your data](https://firebase.google.com/codelabs/ai-genkit-rag#0)

## Who should use Genkit?

Genkit is built for developers adding generative AI to their apps with Node.js or Go, and can run anywhere these runtimes are supported. It works with any generative model API or vector database through [plugins](#plugin-ecosystem).

Developed by the [Firebase](https://firebase.google.com) team, Genkit can be used independently of Firebase or Google Cloud services.

## Get started

- [Node.js quickstart](https://firebase.google.com/docs/genkit/get-started)
- [Next.js quickstart](https://firebase.google.com/docs/genkit/nextjs)
- [Go quickstart](https://firebase.google.com/docs/genkit-go/get-started-go)

> [!NOTE]
> Genkit for Go is in alpha, so we only recommend it for prototyping.

## Library key features

- **Unified generation API:** Generate text, media, structured objects, and tool calls from any generative model using a single, adaptable API.

- **Vector database support:** Add retrieval-augmented generation (RAG) to your apps with simple indexing and retrieval APIs that work across vector database providers.

- **Enhanced prompt engineering:** Define rich prompt templates, model configurations, input/output schemas, and tools all within a single, runnable [.prompt](https://firebase.google.com/docs/genkit/dotprompt) file.

- **AI [work]flows:** Organize your AI app logic into [Flows](https://firebase.google.com/docs/genkit/flows) - functions designed for observability, streaming, integration with Genkit devtools, and easy deployment as API endpoints.

- **Built-in streaming:** Stream content from your Genkit API endpoints to your client app to create snappy user experiences.

## Development tools

Genkit provides a CLI and a web-based Studio to streamline your AI development workflow.

### CLI

The Genkit CLI is the quickest way to start a new Genkit project. It also includes commands for running and assessing your Genkit functions (flows).

- **Install:** `npm i -g genkit`
- **Initialize a new project:** `genkit init`

### Genkit Studio

Genkit Studio offers a web interface for testing, debugging, and iterating on your AI application.

Key features:

- **Run:** Execute and experiment with Genkit flows, prompts, queries, and more in dedicated playgrounds.
- **Inspect:** Analyze detailed traces of past executions, including step-by-step breakdowns of complex flows.
- **Evaluate:** Review the results of evaluations run against your flows, including performance metrics and links to relevant traces.

<img src="docs/resources/readme-ui-traces-screenshot.png" width="700" alt="Screenshot of Genkit Developer UI showing traces">

## Plugin ecosystem

Extend Genkit with plugins for specific AI models, vector databases, and platform integrations from providers like Google and OpenAI.

- **Node.js plugins:** [Explore on npm](https://www.npmjs.com/search?q=keywords:genkit-plugin)
- **Go plugins:** [Explore on pkg.go.dev](https://pkg.go.dev/github.com/firebase/genkit/go#section-directories)

Create and share your own plugins:

- **Write Node.js plugins:** [Plugin Authoring Guide](https://firebase.google.com/docs/genkit/plugin-authoring)
- **Write Go plugins:** (Documentation coming soon)

Find excellent examples of community-built plugins for OpenAI, Anthropic, Cohere, and more in this [repository](https://github.com/TheFireCo/genkit-plugins).

## Try Genkit on IDX

<img src="docs/resources/idx-logo.png" width="50" alt="Project IDX logo">

Want to try Genkit without a local setup? [Explore it on Project IDX](https://idx.google.com/new/genkit), Google's AI-assisted workspace for full-stack app development in the cloud.

## Connect with us

- **Join the community:** Stay updated, ask questions, and share your work with other Genkit users on our [Discord server](https://discord.gg/qXt5zzQKpc).

- **Provide feedback:** Report issues or suggest new features using our GitHub [issue tracker](https://github.com/firebase/genkit/issues).

- **Engage in discussions:** Participate in conversations about Genkit on our [GitHub Discussions](https://github.com/firebase/genkit/discussions) forum.

## Contributing

Contributions to Genkit are welcome and highly appreciated! See our [Contribution Guide](CONTRIBUTING.md) to get started.

## Authors

Genkit is built by [Firebase](https://firebase.google.com/products/genkit) with contributions from the [Open Source Community](https://github.com/firebase/genkit/graphs/contributors).
