# Genkit

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [Genkit documentation](https://firebase.google.com/docs/genkit).

License: Apache 2.0

## API Index

### Classes

| Class | Description |
| :------ | :------ |
| [FirestoreStateStore](classes/FirestoreStateStore.md) | Implementation of flow state store that persistes flow state in Firestore. |
| [Flow](classes/Flow.md) | - |

### Interfaces

| Interface | Description |
| :------ | :------ |
| [FlowAuthPolicy](interfaces/FlowAuthPolicy.md) | - |
| [FlowStateStore](interfaces/FlowStateStore.md) | Flow state store persistence interface. |
| [FlowWrapper](interfaces/FlowWrapper.md) | - |
| [\_\_RequestWithAuth](interfaces/RequestWithAuth.md) | For express-based flows, req.auth should contain the value to bepassed into |

### Type Aliases

| Type alias | Description |
| :------ | :------ |
| [FlowInvokeEnvelopeMessage](type-aliases/FlowInvokeEnvelopeMessage.md) | - |
| [FlowState](type-aliases/FlowState.md) | - |
| [Operation](type-aliases/Operation.md) | - |
| [StepsFunction](type-aliases/StepsFunction.md) | - |

### Variables

| Variable | Description |
| :------ | :------ |
| [FlowInvokeEnvelopeMessageSchema](variables/FlowInvokeEnvelopeMessageSchema.md) | The message format used by the flow task queue and control interface. |
| [FlowStateExecutionSchema](variables/FlowStateExecutionSchema.md) | - |
| [OperationSchema](variables/OperationSchema.md) | Flow Operation, modelled after: |

### Functions

| Function | Description |
| :------ | :------ |
| [defineFlow](functions/defineFlow.md) | Defines the flow. |
| [getFlowAuth](functions/getFlowAuth.md) | Gets the auth object from the current context. |
| [run](functions/run.md) | A flow steap that executes the provided function and memoizes the output. |
| [runAction](functions/runAction.md) | A flow steap that executes an action with provided input and memoizes the output. |
| [runFlow](functions/runFlow.md) | Runs the flow. If the flow does not get interrupted may return a completed (done=true) operation. |
| [runMap](functions/runMap.md) | A helper that takes an array of inputs and maps each input to a run step. |
| [startFlowsServer](functions/startFlowsServer.md) | - |
| [streamFlow](functions/streamFlow.md) | Runs the flow and streams results. If the flow does not get interrupted may return a completed (done=true) operation. |
