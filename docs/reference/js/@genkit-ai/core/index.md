# Genkit

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [Genkit documentation](https://firebase.google.com/docs/genkit).

License: Apache 2.0

## API Index

### Enumerations

| Enumeration | Description |
| :------ | :------ |
| [StatusCodes](enumerations/StatusCodes.md) | - |

### Classes

| Class | Description |
| :------ | :------ |
| [GenkitError](classes/GenkitError.md) | - |

### Interfaces

| Interface | Description |
| :------ | :------ |
| [ActionMetadata](interfaces/ActionMetadata.md) | - |
| [ConfigOptions](interfaces/ConfigOptions.md) | - |
| [FlowStateQuery](interfaces/FlowStateQuery.md) | - |
| [FlowStateQueryResponse](interfaces/FlowStateQueryResponse.md) | - |
| [FlowStateStore](interfaces/FlowStateStore.md) | Flow state store persistence interface. |
| [InitializedPlugin](interfaces/InitializedPlugin.md) | - |
| [LoggerConfig](interfaces/LoggerConfig.md) | Provides a Winston {LoggerOptions} configuration for building a Winston |
| [Middleware](interfaces/Middleware.md) | - |
| [PluginProvider](interfaces/PluginProvider.md) | - |
| [Provider](interfaces/Provider.md) | - |
| [TelemetryConfig](interfaces/TelemetryConfig.md) | Provides a {NodeSDKConfiguration} configuration for use with the |
| [TelemetryOptions](interfaces/TelemetryOptions.md) | Options for configuring the Open-Telemetry export configuration as part of a |

### Type Aliases

| Type alias | Description |
| :------ | :------ |
| [Action](type-aliases/Action.md) | - |
| [FlowError](type-aliases/FlowError.md) | - |
| [FlowState](type-aliases/FlowState.md) | - |
| [FlowStateExecution](type-aliases/FlowStateExecution.md) | - |
| [Operation](type-aliases/Operation.md) | - |
| [Plugin](type-aliases/Plugin.md) | - |
| [SideChannelData](type-aliases/SideChannelData.md) | - |
| [Status](type-aliases/Status.md) | - |
| [StreamingCallback](type-aliases/StreamingCallback.md) | - |

### Variables

| Variable | Description |
| :------ | :------ |
| [FlowErrorSchema](variables/FlowErrorSchema.md) | - |
| [FlowResponseSchema](variables/FlowResponseSchema.md) | - |
| [FlowResultSchema](variables/FlowResultSchema.md) | - |
| [FlowStateExecutionSchema](variables/FlowStateExecutionSchema.md) | - |
| [FlowStateSchema](variables/FlowStateSchema.md) | Defines the format for flow state. This is the format used for persisting the state in |
| [GENKIT\_CLIENT\_HEADER](variables/GENKIT_CLIENT_HEADER.md) | - |
| [GENKIT\_VERSION](variables/GENKIT_VERSION.md) | Copyright 2024 Google LLC |
| [JSONSchema7](variables/JSONSchema7.md) | - |
| [OperationSchema](variables/OperationSchema.md) | Flow Operation, modelled after: |
| [StatusSchema](variables/StatusSchema.md) | - |
| [config](variables/config.md) | - |

### Functions

| Function | Description |
| :------ | :------ |
| [\_\_hardResetConfigForTesting](functions/hardResetConfigForTesting.md) | - |
| [action](functions/action.md) | Creates an action with the provided config. |
| [actionWithMiddleware](functions/actionWithMiddleware.md) | - |
| [configureGenkit](functions/configureGenkit.md) | Configures Genkit with a set of options. This should be called from `genkit.configig.js`. |
| [defineAction](functions/defineAction.md) | Defines an action with the given config and registers it in the registry. |
| [genkitPlugin](functions/genkitPlugin.md) | Defines a Genkit plugin. |
| [getCurrentEnv](functions/getCurrentEnv.md) | - |
| [getStreamingCallback](functions/getStreamingCallback.md) | Retrieves the [StreamingCallback](type-aliases/StreamingCallback.md) previously set by [runWithStreamingCallback](functions/runWithStreamingCallback.md) |
| [initializeGenkit](functions/initializeGenkit.md) | Locates `genkit.config.js` and loads the file so that the config can be registered. |
| [isDevEnv](functions/isDevEnv.md) | Whether current env is `dev`. |
| [runWithStreamingCallback](functions/runWithStreamingCallback.md) | Executes provided function with streaming callback in async local storage which can be retrieved |
