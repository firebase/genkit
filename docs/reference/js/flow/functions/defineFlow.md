# Function: defineFlow()

```ts
function defineFlow<I, O, S>(config: {
  "authPolicy": FlowAuthPolicy<I>;
  "experimentalDurable": boolean;
  "experimentalScheduler": Scheduler<I, O, S>;
  "inputSchema": I;
  "invoker": Invoker<I, O, S>;
  "middleware": RequestHandler<ParamsDictionary, any, any, ParsedQs, Record<string, any>>[];
  "name": string;
  "outputSchema": O;
  "streamSchema": S;
}, steps: StepsFunction<I, O, S>): Flow<I, O, S>
```

Defines the flow.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `ZodType`\<`any`, `any`, `any`, `I`\> | `ZodTypeAny` |
| `O` *extends* `ZodType`\<`any`, `any`, `any`, `O`\> | `ZodTypeAny` |
| `S` *extends* `ZodType`\<`any`, `any`, `any`, `S`\> | `ZodTypeAny` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `config` | `object` |
| `config.authPolicy`? | [`FlowAuthPolicy`](../interfaces/FlowAuthPolicy.md)\<`I`\> |
| `config.experimentalDurable`? | `boolean` |
| `config.experimentalScheduler`? | `Scheduler`\<`I`, `O`, `S`\> |
| `config.inputSchema`? | `I` |
| `config.invoker`? | `Invoker`\<`I`, `O`, `S`\> |
| `config.middleware`? | `RequestHandler`\<`ParamsDictionary`, `any`, `any`, `ParsedQs`, `Record`\<`string`, `any`\>\>[] |
| `config.name` | `string` |
| `config.outputSchema`? | `O` |
| `config.streamSchema`? | `S` |
| `steps` | [`StepsFunction`](../type-aliases/StepsFunction.md)\<`I`, `O`, `S`\> |

## Returns

[`Flow`](../classes/Flow.md)\<`I`, `O`, `S`\>

## Source

[flow/src/flow.ts:106](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L106)
