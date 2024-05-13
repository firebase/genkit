# Firebase Genkit CLI.

To install the CLI

```bash
npm i -g genkit
```

Available commands:

- `init [options]`

  initialize a project directory with Genkit

- `start [options]`

  run the app in dev mode and start a Developer UI

- `flow:run [options] <flowName> [data]`

  run a flow using provided data as input

- `flow:batchRun [options] <flowName> <inputFileName>`

  batch run a flow using provided set of data from a file as input

- `flow:resume <flowName> <flowId> <data>`

  resume an interrupted flow (experimental)

- `eval:extractData [options] <flowName>`

  extract evaludation data for a given flow from the trace store

- `eval:run [options] <dataset>`

  evaluate provided dataset against configured evaluators

- `eval:flow [options] <flowName> [data]`

  evaluate a flow against configured evaluators using provided data as input

- `config`

  set development environment configuration

- `help`
