# Genkit

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [Genkit documentation](https://firebase.google.com/docs/genkit).

License: Apache 2.0

## API Index

### Classes

| Class | Description |
| :------ | :------ |
| [Candidate](classes/Candidate.md) | Candidate represents one of several possible generated responses from a generation |
| [GenerateResponse](classes/GenerateResponse.md) | GenerateResponse is the result from a `generate()` call and contains one or |
| [Message](classes/Message.md) | Message represents a single role's contribution to a generation. Each message |

### Interfaces

| Interface | Description |
| :------ | :------ |
| [EvaluatorReference](interfaces/EvaluatorReference.md) | - |
| [GenerateOptions](interfaces/GenerateOptions.md) | - |
| [GenerateStreamResponse](interfaces/GenerateStreamResponse.md) | - |
| [IndexerReference](interfaces/IndexerReference.md) | - |
| [RetrieverReference](interfaces/RetrieverReference.md) | - |

### Type Aliases

| Type alias | Description |
| :------ | :------ |
| [EvaluatorAction](type-aliases/EvaluatorAction.md) | - |
| [EvaluatorInfo](type-aliases/EvaluatorInfo.md) | - |
| [GenerateStreamOptions](type-aliases/GenerateStreamOptions.md) | - |
| [IndexerAction](type-aliases/IndexerAction.md) | - |
| [IndexerInfo](type-aliases/IndexerInfo.md) | - |
| [LlmResponse](type-aliases/LlmResponse.md) | - |
| [LlmStats](type-aliases/LlmStats.md) | - |
| [ModelId](type-aliases/ModelId.md) | - |
| [PromptAction](type-aliases/PromptAction.md) | - |
| [RetrieverAction](type-aliases/RetrieverAction.md) | - |
| [RetrieverInfo](type-aliases/RetrieverInfo.md) | - |
| [Tool](type-aliases/Tool.md) | - |
| [ToolAction](type-aliases/ToolAction.md) | - |
| [ToolCall](type-aliases/ToolCall.md) | - |

### Variables

| Variable | Description |
| :------ | :------ |
| [CommonLlmOptions](variables/CommonLlmOptions.md) | - |
| [LlmResponseSchema](variables/LlmResponseSchema.md) | - |
| [LlmStatsSchema](variables/LlmStatsSchema.md) | - |
| [ModelIdSchema](variables/ModelIdSchema.md) | - |
| [ToolCallSchema](variables/ToolCallSchema.md) | - |
| [ToolSchema](variables/ToolSchema.md) | - |

### Functions

| Function | Description |
| :------ | :------ |
| [asTool](functions/asTool.md) | - |
| [definePrompt](functions/definePrompt.md) | - |
| [defineTool](functions/defineTool.md) | - |
| [evaluate](functions/evaluate.md) | A veneer for interacting with evaluators. |
| [evaluatorRef](functions/evaluatorRef.md) | Helper method to configure a [EvaluatorReference](interfaces/EvaluatorReference.md) to a plugin. |
| [generate](functions/generate.md) | Generate calls a generative model based on the provided prompt and configuration. If |
| [generateStream](functions/generateStream.md) | - |
| [index](functions/index.md) | Indexes documents using a [IndexerAction](type-aliases/IndexerAction.md) or a DocumentStore. |
| [indexerRef](functions/indexerRef.md) | Helper method to configure a [IndexerReference](interfaces/IndexerReference.md) to a plugin. |
| [renderPrompt](functions/renderPrompt.md) | - |
| [retrieve](functions/retrieve.md) | Retrieves documents from a [RetrieverAction](type-aliases/RetrieverAction.md) based on the provided query. |
| [retrieverRef](functions/retrieverRef.md) | Helper method to configure a [RetrieverReference](interfaces/RetrieverReference.md) to a plugin. |
| [toGenerateRequest](functions/toGenerateRequest.md) | - |
| [toToolWireFormat](functions/toToolWireFormat.md) | Converts actions to tool definition sent to model inputs. |
