# Class: Flow\<I, O, S\>

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |
| `O` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |
| `S` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |

## Constructors

### new Flow()

```ts
new Flow<I, O, S>(config: {
  "authPolicy": FlowAuthPolicy<I>;
  "experimentalDurable": boolean;
  "inputSchema": I;
  "invoker": Invoker<I, O, S>;
  "middleware": RequestHandler<ParamsDictionary, any, any, ParsedQs, Record<string, any>>[];
  "name": string;
  "outputSchema": O;
  "scheduler": Scheduler<I, O, S>;
  "stateStore": () => Promise<FlowStateStore>;
  "streamSchema": S;
}, steps: StepsFunction<I, O, S>): Flow<I, O, S>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `config` | `object` |
| `config.authPolicy`? | [`FlowAuthPolicy`](../interfaces/FlowAuthPolicy.md)\<`I`\> |
| `config.experimentalDurable` | `boolean` |
| `config.inputSchema`? | `I` |
| `config.invoker` | `Invoker`\<`I`, `O`, `S`\> |
| `config.middleware`? | `RequestHandler`\<`ParamsDictionary`, `any`, `any`, `ParsedQs`, `Record`\<`string`, `any`\>\>[] |
| `config.name` | `string` |
| `config.outputSchema`? | `O` |
| `config.scheduler` | `Scheduler`\<`I`, `O`, `S`\> |
| `config.stateStore`? | () => `Promise`\<[`FlowStateStore`](../interfaces/FlowStateStore.md)\> |
| `config.streamSchema`? | `S` |
| `steps` | [`StepsFunction`](../type-aliases/StepsFunction.md)\<`I`, `O`, `S`\> |

#### Returns

[`Flow`](Flow.md)\<`I`, `O`, `S`\>

#### Source

[flow/src/flow.ts:187](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L187)

## Properties

| Property | Modifier | Type |
| :------ | :------ | :------ |
| `authPolicy?` | `readonly` | [`FlowAuthPolicy`](../interfaces/FlowAuthPolicy.md)\<`I`\> |
| `experimentalDurable` | `readonly` | `boolean` |
| `inputSchema?` | `readonly` | `I` |
| `invoker` | `readonly` | `Invoker`\<`I`, `O`, `S`\> |
| `middleware?` | `readonly` | `RequestHandler`\<`ParamsDictionary`, `any`, `any`, `ParsedQs`, `Record`\<`string`, `any`\>\>[] |
| `name` | `readonly` | `string` |
| `outputSchema?` | `readonly` | `O` |
| `scheduler` | `readonly` | `Scheduler`\<`I`, `O`, `S`\> |
| `stateStore?` | `readonly` | () => `Promise`\<[`FlowStateStore`](../interfaces/FlowStateStore.md)\> |
| `steps` | `private` | [`StepsFunction`](../type-aliases/StepsFunction.md)\<`I`, `O`, `S`\> |
| `streamSchema?` | `readonly` | `S` |

## Accessors

### expressHandler

```ts
get expressHandler(): (req: __RequestWithAuth, res: Response<any, Record<string, any>>) => Promise<void>
```

#### Returns

`Function`

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `req` | [`__RequestWithAuth`](../interfaces/RequestWithAuth.md) |
| `res` | `Response`\<`any`, `Record`\<`string`, `any`\>\> |

##### Returns

`Promise`\<`void`\>

#### Source

[flow/src/flow.ts:630](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L630)

## Methods

### durableExpressHandler()

```ts
private durableExpressHandler(req: Request<ParamsDictionary, any, any, ParsedQs, Record<string, any>>, res: Response<any, Record<string, any>>): Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `req` | `Request`\<`ParamsDictionary`, `any`, `any`, `ParsedQs`, `Record`\<`string`, `any`\>\> |
| `res` | `Response`\<`any`, `Record`\<`string`, `any`\>\> |

#### Returns

`Promise`\<`void`\>

#### Source

[flow/src/flow.ts:498](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L498)

***

### executeSteps()

```ts
private executeSteps(
   ctx: Context<I, O, S>, 
   handler: StepsFunction<I, O, S>, 
   dispatchType: string, 
   streamingCallback: undefined | StreamingCallback<any>, 
labels: undefined | Record<string, string>): Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `ctx` | `Context`\<`I`, `O`, `S`\> |
| `handler` | [`StepsFunction`](../type-aliases/StepsFunction.md)\<`I`, `O`, `S`\> |
| `dispatchType` | `string` |
| `streamingCallback` | `undefined` \| `StreamingCallback`\<`any`\> |
| `labels` | `undefined` \| `Record`\<`string`, `string`\> |

#### Returns

`Promise`\<`void`\>

#### Source

[flow/src/flow.ts:386](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L386)

***

### nonDurableExpressHandler()

```ts
private nonDurableExpressHandler(req: __RequestWithAuth, res: Response<any, Record<string, any>>): Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `req` | [`__RequestWithAuth`](../interfaces/RequestWithAuth.md) |
| `res` | `Response`\<`any`, `Record`\<`string`, `any`\>\> |

#### Returns

`Promise`\<`void`\>

#### Source

[flow/src/flow.ts:544](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L544)

***

### runDirectly()

```ts
runDirectly(input: unknown, opts: {
  "auth": unknown;
  "labels": Record<string, string>;
  "streamingCallback": StreamingCallback<unknown>;
 }): Promise<{
  "blockedOnStep": null | {
     "name": string;
     "schema": string;
    };
  "cache": Record<string, {
     "empty": true;
     "value": any;
    }>;
  "eventsTriggered": Record<string, any>;
  "executions": {
     "endTime": number;
     "startTime": number;
     "traceIds": string[];
    }[];
  "flowId": string;
  "input": unknown;
  "name": string;
  "operation": {
     "blockedOnStep": {
        "name": string;
        "schema": string;
       };
     "done": boolean;
     "metadata": any;
     "name": string;
     "result": {
        "response": unknown;
       } & {
        "error": string;
        "stacktrace": string;
       };
    };
  "startTime": number;
  "traceContext": string;
}>
```

Executes the flow with the input directly.

This will either be called by runEnvelope when starting durable flows,
or it will be called directly when starting non-durable flows.

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `input` | `unknown` |
| `opts` | `object` |
| `opts.auth`? | `unknown` |
| `opts.labels`? | `Record`\<`string`, `string`\> |
| `opts.streamingCallback`? | `StreamingCallback`\<`unknown`\> |

#### Returns

`Promise`\<\{
  `"blockedOnStep"`: `null` \| \{
     `"name"`: `string`;
     `"schema"`: `string`;
    \};
  `"cache"`: `Record`\<`string`, \{
     `"empty"`: `true`;
     `"value"`: `any`;
    \}\>;
  `"eventsTriggered"`: `Record`\<`string`, `any`\>;
  `"executions"`: \{
     `"endTime"`: `number`;
     `"startTime"`: `number`;
     `"traceIds"`: `string`[];
    \}[];
  `"flowId"`: `string`;
  `"input"`: `unknown`;
  `"name"`: `string`;
  `"operation"`: \{
     `"blockedOnStep"`: \{
        `"name"`: `string`;
        `"schema"`: `string`;
       \};
     `"done"`: `boolean`;
     `"metadata"`: `any`;
     `"name"`: `string`;
     `"result"`: \{
        `"response"`: `unknown`;
       \} & \{
        `"error"`: `string`;
        `"stacktrace"`: `string`;
       \};
    \};
  `"startTime"`: `number`;
  `"traceContext"`: `string`;
 \}\>

| Member | Type |
| :------ | :------ |
| `blockedOnStep` | `null` \| \{
  `"name"`: `string`;
  `"schema"`: `string`;
 \} |
| `cache` | `Record`\<`string`, \{
  `"empty"`: `true`;
  `"value"`: `any`;
 \}\> |
| `eventsTriggered` | `Record`\<`string`, `any`\> |
| `executions` | \{
  `"endTime"`: `number`;
  `"startTime"`: `number`;
  `"traceIds"`: `string`[];
 \}[] |
| `flowId` | `string` |
| `input` | `unknown` |
| `name` | `string` |
| `operation` | \{
  `"blockedOnStep"`: \{
     `"name"`: `string`;
     `"schema"`: `string`;
    \};
  `"done"`: `boolean`;
  `"metadata"`: `any`;
  `"name"`: `string`;
  `"result"`: \{
     `"response"`: `unknown`;
    \} & \{
     `"error"`: `string`;
     `"stacktrace"`: `string`;
    \};
 \} |
| `operation.blockedOnStep` | \{
  `"name"`: `string`;
  `"schema"`: `string`;
 \} |
| `operation.blockedOnStep.name` | `string` |
| `operation.blockedOnStep.schema` | `string` |
| `operation.done` | `boolean` |
| `operation.metadata` | `any` |
| `operation.name` | `string` |
| `operation.result` | \{
  `"response"`: `unknown`;
 \} & \{
  `"error"`: `string`;
  `"stacktrace"`: `string`;
 \} |
| `startTime` | `number` |
| `traceContext` | `string` |

#### Source

[flow/src/flow.ts:226](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L226)

***

### runEnvelope()

```ts
runEnvelope(
   req: {
  "resume": {
     "flowId": string;
     "payload": unknown;
    };
  "retry": {
     "flowId": string;
    };
  "runScheduled": {
     "flowId": string;
    };
  "schedule": {
     "delay": number;
     "input": unknown;
    };
  "start": {
     "input": unknown;
     "labels": Record<string, string>;
    };
  "state": {
     "flowId": string;
    };
 }, 
   streamingCallback?: StreamingCallback<any>, 
   auth?: unknown): Promise<{
  "blockedOnStep": null | {
     "name": string;
     "schema": string;
    };
  "cache": Record<string, {
     "empty": true;
     "value": any;
    }>;
  "eventsTriggered": Record<string, any>;
  "executions": {
     "endTime": number;
     "startTime": number;
     "traceIds": string[];
    }[];
  "flowId": string;
  "input": unknown;
  "name": string;
  "operation": {
     "blockedOnStep": {
        "name": string;
        "schema": string;
       };
     "done": boolean;
     "metadata": any;
     "name": string;
     "result": {
        "response": unknown;
       } & {
        "error": string;
        "stacktrace": string;
       };
    };
  "startTime": number;
  "traceContext": string;
}>
```

Executes the flow with the input in the envelope format.

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `req` | `object` |
| `req.resume`? | `object` |
| `req.resume.flowId`? | `string` |
| `req.resume.payload`? | `unknown` |
| `req.retry`? | `object` |
| `req.retry.flowId`? | `string` |
| `req.runScheduled`? | `object` |
| `req.runScheduled.flowId`? | `string` |
| `req.schedule`? | `object` |
| `req.schedule.delay`? | `number` |
| `req.schedule.input`? | `unknown` |
| `req.start`? | `object` |
| `req.start.input`? | `unknown` |
| `req.start.labels`? | `Record`\<`string`, `string`\> |
| `req.state`? | `object` |
| `req.state.flowId`? | `string` |
| `streamingCallback`? | `StreamingCallback`\<`any`\> |
| `auth`? | `unknown` |

#### Returns

`Promise`\<\{
  `"blockedOnStep"`: `null` \| \{
     `"name"`: `string`;
     `"schema"`: `string`;
    \};
  `"cache"`: `Record`\<`string`, \{
     `"empty"`: `true`;
     `"value"`: `any`;
    \}\>;
  `"eventsTriggered"`: `Record`\<`string`, `any`\>;
  `"executions"`: \{
     `"endTime"`: `number`;
     `"startTime"`: `number`;
     `"traceIds"`: `string`[];
    \}[];
  `"flowId"`: `string`;
  `"input"`: `unknown`;
  `"name"`: `string`;
  `"operation"`: \{
     `"blockedOnStep"`: \{
        `"name"`: `string`;
        `"schema"`: `string`;
       \};
     `"done"`: `boolean`;
     `"metadata"`: `any`;
     `"name"`: `string`;
     `"result"`: \{
        `"response"`: `unknown`;
       \} & \{
        `"error"`: `string`;
        `"stacktrace"`: `string`;
       \};
    \};
  `"startTime"`: `number`;
  `"traceContext"`: `string`;
 \}\>

| Member | Type |
| :------ | :------ |
| `blockedOnStep` | `null` \| \{
  `"name"`: `string`;
  `"schema"`: `string`;
 \} |
| `cache` | `Record`\<`string`, \{
  `"empty"`: `true`;
  `"value"`: `any`;
 \}\> |
| `eventsTriggered` | `Record`\<`string`, `any`\> |
| `executions` | \{
  `"endTime"`: `number`;
  `"startTime"`: `number`;
  `"traceIds"`: `string`[];
 \}[] |
| `flowId` | `string` |
| `input` | `unknown` |
| `name` | `string` |
| `operation` | \{
  `"blockedOnStep"`: \{
     `"name"`: `string`;
     `"schema"`: `string`;
    \};
  `"done"`: `boolean`;
  `"metadata"`: `any`;
  `"name"`: `string`;
  `"result"`: \{
     `"response"`: `unknown`;
    \} & \{
     `"error"`: `string`;
     `"stacktrace"`: `string`;
    \};
 \} |
| `operation.blockedOnStep` | \{
  `"name"`: `string`;
  `"schema"`: `string`;
 \} |
| `operation.blockedOnStep.name` | `string` |
| `operation.blockedOnStep.schema` | `string` |
| `operation.done` | `boolean` |
| `operation.metadata` | `any` |
| `operation.name` | `string` |
| `operation.result` | \{
  `"response"`: `unknown`;
 \} & \{
  `"error"`: `string`;
  `"stacktrace"`: `string`;
 \} |
| `startTime` | `number` |
| `traceContext` | `string` |

#### Source

[flow/src/flow.ts:256](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L256)
