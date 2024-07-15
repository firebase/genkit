![Firebase Genkit logo](docs/resources/genkit-logo-dark.png#gh-dark-mode-only 'Firebase Genkit')
![Firebase Genkit logo](docs/resources/genkit-logo.png#gh-light-mode-only 'Firebase Genkit')

Firebase Genkit is a framework for TypeScript and Go, designed to help you build and iterate on AI-powered applications and features. It provides open source libraries and integrated tooling to support your AI app development.

## Who is Genkit for?

Genkit is for any developer who wants to integrate generative AI capabilities into their apps using TypeScript or Go. Code written with Genkit libraries can be deployed anywhere that supports Node.js and Go runtimes, and the framework supports any model and vector store provider.

Genkit is built by Firebase, Google's app development platform, but does not require you to be a Firebase or Google Cloud user.

## Why use Genkit?

Integrating generative AI into apps is complicated. You may need to tie together various components like generative AI models (LLMs), prompts, vector stores, embedders, and tools - each with provider-specific implementations and quirks. The non-deterministic nature of generative AI models also makes refining AI apps for production challenging.

Genkit libraries provide lightweight abstractions and unified APIs that make it easy to define and compose AI app components from any provider into cohesive workflows with built-in type-safety and observability. Genkit's integrated tooling accelerates your iteration speed by helping you quickly test, visualize, and debug your app's AI logic.

## Get started

- [Genkit TypeScript (Node.js) documentation](https://firebase.google.com/docs/genkit/get-started)
- [Genkit Go documentation](https://github.com/firebase/genkit/blob/main/docs-go/get-started-go.md)

> [!NOTE]
> Genkit for Go is currently in Alpha, so we only recommend using it for prototyping and exploration. 

## Framework key features

- **Unified APIs for generation and retrieval:** Use standardized APIs to generate, embed, index, and retrieve content with multiple AI model and vector store providers. The generation API supports streaming, structured output with custom schemas, multimodal input and output, function calling with tools, and custom configuration options. Make your code more flexible without sacrificing any provider-specific capabilities.

- **Flows for multistep logic:** Write your AI app logic within observable, type-safe, streamable functions, called [flows](https://firebase.google.com/docs/genkit/flows). Flows are just like regular functions, but are integrated with Genkit tooling, group traces for multiple steps, are deployable as HTTP endpoints with minimal boilerplate, and have additional properties that make them well-suited to working with generative AI APIs. 

- **Enhanced prompt engineering and management:** Your choice of model, configurations, input prompt, output schema, and more all impact your generation outcomes. streamline your prompt engineering process with [Dotprompt](https://firebase.google.com/docs/genkit/dotprompt), a prompt standard that encapsulates rich prompt text and formatting with model and generation metadata. Organize, test, version, and deploy your prompts alongside your code.

- **Easy streaming:** Stream content from your deployed Genkit endpoints directly to your client app to create user experiences that feel faster and more responsive.

- **Extensibile with plugins:** Use plugins built by the Genkit team and community to access components from specific AI model and vector store providers, and integrate with platforms like Firebase, Google Cloud, and more. 

## Tooling

Genkit provides a dedicated CLI and UI that help you get started quickly and rapidly iterate on your AI app.

### CLI

The Genkit CLI is the fastest way to initialize a Genkit app and comes with commands to help you run and evaluate Genkit functions, called flows. 

**Intall the CLI:** `npm i -g genkit`

**Initialize a Genkit app:** `genkit init`

### Developer UI

The Genkit Developer UI helps you rapidly test, debug, and iterate on your AI app using a rich web interface. Key features include:

- **Run:** Invoke and iterate on Genkit flows, prompts, queries, and more in dedicated playgrounds for Genkit components.
- **Inpsect:** View detailed traces for previous exeuctions of flows and components, including step-by-step views of complex flows.
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