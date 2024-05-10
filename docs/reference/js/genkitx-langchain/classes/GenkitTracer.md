# Class: GenkitTracer

## Extends

- `BaseTracer`

## Constructors

### new GenkitTracer()

```ts
new GenkitTracer(_fields?: BaseCallbackHandlerInput): GenkitTracer
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `_fields`? | `BaseCallbackHandlerInput` |

#### Returns

[`GenkitTracer`](GenkitTracer.md)

#### Inherited from

`BaseTracer.constructor`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:29

## Properties

| Property | Modifier | Type | Default value | Overrides | Inherited from |
| :------ | :------ | :------ | :------ | :------ | :------ |
| `awaitHandlers` | `public` | `boolean` | `undefined` | `BaseTracer.awaitHandlers` | `BaseTracer.awaitHandlers` |
| `ignoreAgent` | `public` | `boolean` | `undefined` | `BaseTracer.ignoreAgent` | `BaseTracer.ignoreAgent` |
| `ignoreChain` | `public` | `boolean` | `undefined` | `BaseTracer.ignoreChain` | `BaseTracer.ignoreChain` |
| `ignoreLLM` | `public` | `boolean` | `undefined` | `BaseTracer.ignoreLLM` | `BaseTracer.ignoreLLM` |
| `ignoreRetriever` | `public` | `boolean` | `undefined` | `BaseTracer.ignoreRetriever` | `BaseTracer.ignoreRetriever` |
| `lc_kwargs` | `public` | `SerializedFields` | `undefined` | `BaseTracer.lc_kwargs` | `BaseTracer.lc_kwargs` |
| `lc_serializable` | `public` | `boolean` | `undefined` | `BaseTracer.lc_serializable` | `BaseTracer.lc_serializable` |
| `name` | `public` | `"genkit_callback_handler"` | `...` | `BaseTracer.name` | `BaseTracer.name` |
| `runMap` | `protected` | `Map`\<`string`, `Run`\> | `undefined` | `BaseTracer.runMap` | `BaseTracer.runMap` |
| `spans` | `public` | `Record`\<`string`, `Span`\> | `{}` | - | - |
| `tracer` | `public` | `Tracer` | `...` | - | - |

## Accessors

### lc\_aliases

```ts
get lc_aliases(): undefined | {}
```

#### Returns

`undefined` \| \{\}

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/callbacks/base.d.ts:151

***

### lc\_attributes

```ts
get lc_attributes(): undefined | {}
```

#### Returns

`undefined` \| \{\}

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/callbacks/base.d.ts:148

***

### lc\_id

```ts
get lc_id(): string[]
```

The final serialized identifier for the module.

#### Returns

`string`[]

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/callbacks/base.d.ts:164

***

### lc\_namespace

```ts
get lc_namespace(): ["langchain_core", "callbacks", string]
```

#### Returns

[`"langchain_core"`, `"callbacks"`, `string`]

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/callbacks/base.d.ts:144

***

### lc\_secrets

```ts
get lc_secrets(): undefined | {}
```

#### Returns

`undefined` \| \{\}

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/callbacks/base.d.ts:145

## Methods

### \_addChildRun()

```ts
protected _addChildRun(parentRun: Run, childRun: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `parentRun` | `Run` |
| `childRun` | `Run` |

#### Returns

`void`

#### Inherited from

`BaseTracer._addChildRun`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:33

***

### \_endTrace()

```ts
protected _endTrace(run: Run): Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`Promise`\<`void`\>

#### Inherited from

`BaseTracer._endTrace`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:35

***

### \_getExecutionOrder()

```ts
protected _getExecutionOrder(parentRunId: undefined | string): number
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `parentRunId` | `undefined` \| `string` |

#### Returns

`number`

#### Inherited from

`BaseTracer._getExecutionOrder`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:36

***

### \_startTrace()

```ts
protected _startTrace(run: Run): Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`Promise`\<`void`\>

#### Inherited from

`BaseTracer._startTrace`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:34

***

### copy()

```ts
copy(): this
```

#### Returns

`this`

#### Inherited from

`BaseTracer.copy`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:30

***

### endSpan()

```ts
private endSpan(run: Run, attributes?: Record<string, string>): Span
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |
| `attributes`? | `Record`\<`string`, `string`\> |

#### Returns

`Span`

#### Source

[plugins/langchain/src/tracing.ts:82](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L82)

***

### getBreadcrumbs()

```ts
getBreadcrumbs(run: Run): string
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`string`

#### Source

[plugins/langchain/src/tracing.ts:53](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L53)

***

### getParents()

```ts
getParents(run: Run): Run[]
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`Run`[]

#### Source

[plugins/langchain/src/tracing.ts:38](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L38)

***

### handleAgentAction()

```ts
handleAgentAction(action: AgentAction, runId: string): Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `action` | `AgentAction` |
| `runId` | `string` |

#### Returns

`Promise`\<`void`\>

#### Inherited from

`BaseTracer.handleAgentAction`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:51

***

### handleAgentEnd()

```ts
handleAgentEnd(action: AgentFinish, runId: string): Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `action` | `AgentFinish` |
| `runId` | `string` |

#### Returns

`Promise`\<`void`\>

#### Inherited from

`BaseTracer.handleAgentEnd`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:52

***

### handleChainEnd()

```ts
handleChainEnd(
   outputs: ChainValues, 
   runId: string, 
   _parentRunId?: string, 
   _tags?: string[], 
   kwargs?: {
  "inputs": Record<string, unknown>;
}): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `outputs` | `ChainValues` |
| `runId` | `string` |
| `_parentRunId`? | `string` |
| `_tags`? | `string`[] |
| `kwargs`? | `object` |
| `kwargs.inputs`? | `Record`\<`string`, `unknown`\> |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleChainEnd`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:42

***

### handleChainError()

```ts
handleChainError(
   error: unknown, 
   runId: string, 
   _parentRunId?: string, 
   _tags?: string[], 
   kwargs?: {
  "inputs": Record<string, unknown>;
}): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `error` | `unknown` |
| `runId` | `string` |
| `_parentRunId`? | `string` |
| `_tags`? | `string`[] |
| `kwargs`? | `object` |
| `kwargs.inputs`? | `Record`\<`string`, `unknown`\> |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleChainError`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:45

***

### handleChainStart()

```ts
handleChainStart(
   chain: Serialized, 
   inputs: ChainValues, 
   runId: string, 
   parentRunId?: string, 
   tags?: string[], 
   metadata?: KVMap, 
   runType?: string, 
name?: string): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `chain` | `Serialized` |
| `inputs` | `ChainValues` |
| `runId` | `string` |
| `parentRunId`? | `string` |
| `tags`? | `string`[] |
| `metadata`? | `KVMap` |
| `runType`? | `string` |
| `name`? | `string` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleChainStart`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:41

***

### handleChatModelStart()

```ts
handleChatModelStart(
   llm: Serialized, 
   messages: BaseMessage[][], 
   runId: string, 
   parentRunId?: string, 
   extraParams?: KVMap, 
   tags?: string[], 
   metadata?: KVMap, 
name?: string): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `llm` | `Serialized` |
| `messages` | `BaseMessage`[][] |
| `runId` | `string` |
| `parentRunId`? | `string` |
| `extraParams`? | `KVMap` |
| `tags`? | `string`[] |
| `metadata`? | `KVMap` |
| `name`? | `string` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleChatModelStart`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:38

***

### handleLLMEnd()

```ts
handleLLMEnd(output: LLMResult, runId: string): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `output` | `LLMResult` |
| `runId` | `string` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleLLMEnd`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:39

***

### handleLLMError()

```ts
handleLLMError(error: unknown, runId: string): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `error` | `unknown` |
| `runId` | `string` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleLLMError`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:40

***

### handleLLMNewToken()

```ts
handleLLMNewToken(
   token: string, 
   idx: NewTokenIndices, 
   runId: string, 
   _parentRunId?: string, 
   _tags?: string[], 
fields?: HandleLLMNewTokenCallbackFields): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `token` | `string` |
| `idx` | `NewTokenIndices` |
| `runId` | `string` |
| `_parentRunId`? | `string` |
| `_tags`? | `string`[] |
| `fields`? | `HandleLLMNewTokenCallbackFields` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleLLMNewToken`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:57

***

### handleLLMStart()

```ts
handleLLMStart(
   llm: Serialized, 
   prompts: string[], 
   runId: string, 
   parentRunId?: string, 
   extraParams?: KVMap, 
   tags?: string[], 
   metadata?: KVMap, 
name?: string): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `llm` | `Serialized` |
| `prompts` | `string`[] |
| `runId` | `string` |
| `parentRunId`? | `string` |
| `extraParams`? | `KVMap` |
| `tags`? | `string`[] |
| `metadata`? | `KVMap` |
| `name`? | `string` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleLLMStart`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:37

***

### handleRetrieverEnd()

```ts
handleRetrieverEnd(documents: Document<Record<string, unknown>>[], runId: string): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `documents` | `Document`\<`Record`\<`string`, `unknown`\>\>[] |
| `runId` | `string` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleRetrieverEnd`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:54

***

### handleRetrieverError()

```ts
handleRetrieverError(error: unknown, runId: string): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `error` | `unknown` |
| `runId` | `string` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleRetrieverError`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:55

***

### handleRetrieverStart()

```ts
handleRetrieverStart(
   retriever: Serialized, 
   query: string, 
   runId: string, 
   parentRunId?: string, 
   tags?: string[], 
   metadata?: KVMap, 
name?: string): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `retriever` | `Serialized` |
| `query` | `string` |
| `runId` | `string` |
| `parentRunId`? | `string` |
| `tags`? | `string`[] |
| `metadata`? | `KVMap` |
| `name`? | `string` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleRetrieverStart`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:53

***

### handleText()

```ts
handleText(text: string, runId: string): Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `text` | `string` |
| `runId` | `string` |

#### Returns

`Promise`\<`void`\>

#### Inherited from

`BaseTracer.handleText`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:56

***

### handleToolEnd()

```ts
handleToolEnd(output: string, runId: string): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `output` | `string` |
| `runId` | `string` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleToolEnd`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:49

***

### handleToolError()

```ts
handleToolError(error: unknown, runId: string): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `error` | `unknown` |
| `runId` | `string` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleToolError`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:50

***

### handleToolStart()

```ts
handleToolStart(
   tool: Serialized, 
   input: string, 
   runId: string, 
   parentRunId?: string, 
   tags?: string[], 
   metadata?: KVMap, 
name?: string): Promise<Run>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `tool` | `Serialized` |
| `input` | `string` |
| `runId` | `string` |
| `parentRunId`? | `string` |
| `tags`? | `string`[] |
| `metadata`? | `KVMap` |
| `name`? | `string` |

#### Returns

`Promise`\<`Run`\>

#### Inherited from

`BaseTracer.handleToolStart`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:48

***

### maybeFlattenInput()

```ts
private maybeFlattenInput(input: any): any
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `input` | `any` |

#### Returns

`any`

#### Source

[plugins/langchain/src/tracing.ts:157](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L157)

***

### maybeFlattenOutput()

```ts
private maybeFlattenOutput(output: any): any
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `output` | `any` |

#### Returns

`any`

#### Source

[plugins/langchain/src/tracing.ts:168](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L168)

***

### onAgentAction()

```ts
onAgentAction(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onAgentAction`

#### Source

[plugins/langchain/src/tracing.ts:152](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L152)

***

### onAgentEnd()?

```ts
optional onAgentEnd(run: Run): void | Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void` \| `Promise`\<`void`\>

#### Inherited from

`BaseTracer.onAgentEnd`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:70

***

### onChainEnd()

```ts
onChainEnd(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onChainEnd`

#### Source

[plugins/langchain/src/tracing.ts:108](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L108)

***

### onChainError()

```ts
onChainError(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onChainError`

#### Source

[plugins/langchain/src/tracing.ts:112](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L112)

***

### onChainStart()

```ts
onChainStart(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onChainStart`

#### Source

[plugins/langchain/src/tracing.ts:104](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L104)

***

### onLLMEnd()

```ts
onLLMEnd(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onLLMEnd`

#### Source

[plugins/langchain/src/tracing.ts:120](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L120)

***

### onLLMError()

```ts
onLLMError(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onLLMError`

#### Source

[plugins/langchain/src/tracing.ts:124](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L124)

***

### onLLMNewToken()?

```ts
optional onLLMNewToken(
   run: Run, 
   token: string, 
   kwargs?: {
  "chunk": any;
}): void | Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |
| `token` | `string` |
| `kwargs`? | `object` |
| `kwargs.chunk`? | `any` |

#### Returns

`void` \| `Promise`\<`void`\>

#### Inherited from

`BaseTracer.onLLMNewToken`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:75

***

### onLLMStart()

```ts
onLLMStart(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onLLMStart`

#### Source

[plugins/langchain/src/tracing.ts:116](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L116)

***

### onRetrieverEnd()

```ts
onRetrieverEnd(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onRetrieverEnd`

#### Source

[plugins/langchain/src/tracing.ts:144](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L144)

***

### onRetrieverError()

```ts
onRetrieverError(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onRetrieverError`

#### Source

[plugins/langchain/src/tracing.ts:148](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L148)

***

### onRetrieverStart()

```ts
onRetrieverStart(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onRetrieverStart`

#### Source

[plugins/langchain/src/tracing.ts:140](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L140)

***

### onRunCreate()?

```ts
optional onRunCreate(run: Run): void | Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void` \| `Promise`\<`void`\>

#### Inherited from

`BaseTracer.onRunCreate`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:58

***

### onRunUpdate()?

```ts
optional onRunUpdate(run: Run): void | Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void` \| `Promise`\<`void`\>

#### Inherited from

`BaseTracer.onRunUpdate`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:59

***

### onText()?

```ts
optional onText(run: Run): void | Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void` \| `Promise`\<`void`\>

#### Inherited from

`BaseTracer.onText`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:74

***

### onToolEnd()

```ts
onToolEnd(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onToolEnd`

#### Source

[plugins/langchain/src/tracing.ts:132](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L132)

***

### onToolError()

```ts
onToolError(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onToolError`

#### Source

[plugins/langchain/src/tracing.ts:136](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L136)

***

### onToolStart()

```ts
onToolStart(run: Run): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`void`

#### Overrides

`BaseTracer.onToolStart`

#### Source

[plugins/langchain/src/tracing.ts:128](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L128)

***

### persistRun()

```ts
protected persistRun(_run: Run): Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `_run` | `Run` |

#### Returns

`Promise`\<`void`\>

#### Overrides

`BaseTracer.persistRun`

#### Source

[plugins/langchain/src/tracing.ts:34](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L34)

***

### startSpan()

```ts
private startSpan(run: Run): Span
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `run` | `Run` |

#### Returns

`Span`

#### Source

[plugins/langchain/src/tracing.ts:58](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/tracing.ts#L58)

***

### stringifyError()

```ts
protected stringifyError(error: unknown): string
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `error` | `unknown` |

#### Returns

`string`

#### Inherited from

`BaseTracer.stringifyError`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/tracers/base.d.ts:31

***

### toJSON()

```ts
toJSON(): Serialized
```

#### Returns

`Serialized`

#### Inherited from

`BaseTracer.toJSON`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/callbacks/base.d.ts:174

***

### toJSONNotImplemented()

```ts
toJSONNotImplemented(): SerializedNotImplemented
```

#### Returns

`SerializedNotImplemented`

#### Inherited from

`BaseTracer.toJSONNotImplemented`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/callbacks/base.d.ts:175

***

### fromMethods()

```ts
static fromMethods(methods: BaseCallbackHandlerMethodsClass): {
  "awaitHandlers": boolean;
  "ignoreAgent": boolean;
  "ignoreChain": boolean;
  "ignoreLLM": boolean;
  "ignoreRetriever": boolean;
  "lc_aliases": undefined | {};
  "lc_attributes": undefined | {};
  "lc_id": string[];
  "lc_kwargs": SerializedFields;
  "lc_namespace": ["langchain_core", "callbacks", string];
  "lc_secrets": undefined | {};
  "lc_serializable": boolean;
  "name": string;
  "copy": BaseCallbackHandler;
  "handleAgentAction": void | Promise<void>;
  "handleAgentEnd": void | Promise<void>;
  "handleChainEnd": any;
  "handleChainError": any;
  "handleChainStart": any;
  "handleChatModelStart": any;
  "handleLLMEnd": any;
  "handleLLMError": any;
  "handleLLMNewToken": any;
  "handleLLMStart": any;
  "handleRetrieverEnd": any;
  "handleRetrieverError": any;
  "handleRetrieverStart": any;
  "handleText": void | Promise<void>;
  "handleToolEnd": any;
  "handleToolError": any;
  "handleToolStart": any;
  "toJSON": Serialized;
  "toJSONNotImplemented": SerializedNotImplemented;
}
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `methods` | `BaseCallbackHandlerMethodsClass` |

#### Returns

```ts
{
  "awaitHandlers": boolean;
  "ignoreAgent": boolean;
  "ignoreChain": boolean;
  "ignoreLLM": boolean;
  "ignoreRetriever": boolean;
  "lc_aliases": undefined | {};
  "lc_attributes": undefined | {};
  "lc_id": string[];
  "lc_kwargs": SerializedFields;
  "lc_namespace": ["langchain_core", "callbacks", string];
  "lc_secrets": undefined | {};
  "lc_serializable": boolean;
  "name": string;
  "copy": BaseCallbackHandler;
  "handleAgentAction": void | Promise<void>;
  "handleAgentEnd": void | Promise<void>;
  "handleChainEnd": any;
  "handleChainError": any;
  "handleChainStart": any;
  "handleChatModelStart": any;
  "handleLLMEnd": any;
  "handleLLMError": any;
  "handleLLMNewToken": any;
  "handleLLMStart": any;
  "handleRetrieverEnd": any;
  "handleRetrieverError": any;
  "handleRetrieverStart": any;
  "handleText": void | Promise<void>;
  "handleToolEnd": any;
  "handleToolError": any;
  "handleToolStart": any;
  "toJSON": Serialized;
  "toJSONNotImplemented": SerializedNotImplemented;
}
```

| Member | Type | Description |
| :------ | :------ | :------ |
| `awaitHandlers` | `boolean` | - |
| `ignoreAgent` | `boolean` | - |
| `ignoreChain` | `boolean` | - |
| `ignoreLLM` | `boolean` | - |
| `ignoreRetriever` | `boolean` | - |
| `lc_aliases` | `undefined` \| \{\} | - |
| `lc_attributes` | `undefined` \| \{\} | - |
| `lc_id` | `string`[] | The final serialized identifier for the module. |
| `lc_kwargs` | `SerializedFields` | - |
| `lc_namespace` | [`"langchain_core"`, `"callbacks"`, `string`] | - |
| `lc_secrets` | `undefined` \| \{\} | - |
| `lc_serializable` | `boolean` | - |
| `name` | `string` | - |
| `copy` | `BaseCallbackHandler` | - |
| `handleAgentAction` | `void` \| `Promise`\<`void`\> | Called when an agent is about to execute an action,<br />with the action and the run ID. |
| `handleAgentEnd` | `void` \| `Promise`\<`void`\> | Called when an agent finishes execution, before it exits.<br />with the final output and the run ID. |
| `handleChainEnd` | `any` | Called at the end of a Chain run, with the outputs and the run ID. |
| `handleChainError` | `any` | Called if a Chain run encounters an error |
| `handleChainStart` | `any` | Called at the start of a Chain run, with the chain name and inputs<br />and the run ID. |
| `handleChatModelStart` | `any` | Called at the start of a Chat Model run, with the prompt(s)<br />and the run ID. |
| `handleLLMEnd` | `any` | Called at the end of an LLM/ChatModel run, with the output and the run ID. |
| `handleLLMError` | `any` | Called if an LLM/ChatModel run encounters an error |
| `handleLLMNewToken` | `any` | Called when an LLM/ChatModel in `streaming` mode produces a new token |
| `handleLLMStart` | `any` | Called at the start of an LLM or Chat Model run, with the prompt(s)<br />and the run ID. |
| `handleRetrieverEnd` | `any` | - |
| `handleRetrieverError` | `any` | - |
| `handleRetrieverStart` | `any` | - |
| `handleText` | `void` \| `Promise`\<`void`\> | - |
| `handleToolEnd` | `any` | Called at the end of a Tool run, with the tool output and the run ID. |
| `handleToolError` | `any` | Called if a Tool run encounters an error |
| `handleToolStart` | `any` | Called at the start of a Tool run, with the tool name and input<br />and the run ID. |
| `toJSON` | `Serialized` | - |
| `toJSONNotImplemented` | `SerializedNotImplemented` | - |

#### Inherited from

`BaseTracer.fromMethods`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/callbacks/base.d.ts:176

***

### lc\_name()

```ts
static lc_name(): string
```

The name of the serializable. Override to provide an alias or
to preserve the serialized module name in minified environments.

Implemented as a static method to support loading logic.

#### Returns

`string`

#### Inherited from

`BaseTracer.lc_name`

#### Source

node\_modules/.pnpm/@langchain+core@0.1.61/node\_modules/@langchain/core/dist/callbacks/base.d.ts:160
