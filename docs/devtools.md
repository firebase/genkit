# Firebase Genkit Developer Tools

Firebase Genkit comes with two sets of developer tools:

- A Node.js CLI
- An optonal local web app that can connect to your Genkit configuration

### Command Line Interface

Install the CLI with the following command:

```posix-terminal
npm install genkit
```

The CLI offers many useful commands to work with Genkit projects including:

- `genkit init`: initialize a Genkit project
- `genkit flow:run flowName`: run a flow
- `genkit eval:flow flowName`: evaluate a flow

See all the available commands with:

```posix-terminal
npx genkit --help
```

### Genkit Developer UI

The Genkit developer UI is a local web app that you can use to interact with the models, retrievers, flows and other actions in your Genkit project.

Download and start the developer UI with:

```posix-terminal
npx genkit start
```

The UI will load in your default browser:

![Welcome to Genkit Developer UI](resources/welcome_to_genkit_developer_ui.png)

The Developer UI has action runners for `flow`, `prompt`, `model`, `tool`, `retreiver`, `indexer`, `embedder` and `evaluator` configured in your `genkit.conf` file.

Here's a quick gif tour with cats.

![Gif overview of Genkit Developer UI](resources/genkit_developer_ui_overview.gif)
