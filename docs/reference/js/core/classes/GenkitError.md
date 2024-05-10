# Class: GenkitError

## Extends

- `Error`

## Constructors

### new GenkitError()

```ts
new GenkitError(__namedParameters: {
  "detail": any;
  "message": string;
  "source": string;
  "status":   | "CANCELLED"
     | "UNKNOWN"
     | "INVALID_ARGUMENT"
     | "DEADLINE_EXCEEDED"
     | "NOT_FOUND"
     | "ALREADY_EXISTS"
     | "PERMISSION_DENIED"
     | "UNAUTHENTICATED"
     | "RESOURCE_EXHAUSTED"
     | "FAILED_PRECONDITION"
     | "ABORTED"
     | "OUT_OF_RANGE"
     | "UNIMPLEMENTED"
     | "INTERNAL"
     | "UNAVAILABLE"
     | "DATA_LOSS";
 }): GenkitError
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `__namedParameters` | `object` |
| `__namedParameters.detail`? | `any` |
| `__namedParameters.message` | `string` |
| `__namedParameters.source`? | `string` |
| `__namedParameters.status` |  \| `"CANCELLED"` \| `"UNKNOWN"` \| `"INVALID_ARGUMENT"` \| `"DEADLINE_EXCEEDED"` \| `"NOT_FOUND"` \| `"ALREADY_EXISTS"` \| `"PERMISSION_DENIED"` \| `"UNAUTHENTICATED"` \| `"RESOURCE_EXHAUSTED"` \| `"FAILED_PRECONDITION"` \| `"ABORTED"` \| `"OUT_OF_RANGE"` \| `"UNIMPLEMENTED"` \| `"INTERNAL"` \| `"UNAVAILABLE"` \| `"DATA_LOSS"` |

#### Returns

[`GenkitError`](GenkitError.md)

#### Overrides

`Error.constructor`

#### Source

[core/src/error.ts:24](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/core/src/error.ts#L24)

## Properties

| Property | Modifier | Type | Description | Inherited from |
| :------ | :------ | :------ | :------ | :------ |
| `detail?` | `public` | `any` | - | - |
| `message` | `public` | `string` | - | `Error.message` |
| `name` | `public` | `string` | - | `Error.name` |
| `source?` | `public` | `string` | - | - |
| `stack?` | `public` | `string` | - | `Error.stack` |
| `status` | `public` |  \| `"CANCELLED"` \| `"UNKNOWN"` \| `"INVALID_ARGUMENT"` \| `"DEADLINE_EXCEEDED"` \| `"NOT_FOUND"` \| `"ALREADY_EXISTS"` \| `"PERMISSION_DENIED"` \| `"UNAUTHENTICATED"` \| `"RESOURCE_EXHAUSTED"` \| `"FAILED_PRECONDITION"` \| `"ABORTED"` \| `"OUT_OF_RANGE"` \| `"UNIMPLEMENTED"` \| `"INTERNAL"` \| `"UNAVAILABLE"` \| `"DATA_LOSS"` | - | - |
| `prepareStackTrace?` | `static` | (`err`: `Error`, `stackTraces`: `CallSite`[]) => `any` | Optional override for formatting stack traces<br /><br />**See**<br />https://v8.dev/docs/stack-trace-api#customizing-stack-traces | `Error.prepareStackTrace` |
| `stackTraceLimit` | `static` | `number` | - | `Error.stackTraceLimit` |

## Methods

### captureStackTrace()

```ts
static captureStackTrace(targetObject: object, constructorOpt?: Function): void
```

Create .stack property on a target object

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `targetObject` | `object` |
| `constructorOpt`? | `Function` |

#### Returns

`void`

#### Inherited from

`Error.captureStackTrace`

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/globals.d.ts:21
