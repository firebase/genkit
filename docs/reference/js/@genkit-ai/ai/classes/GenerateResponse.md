# Class: GenerateResponse\<O\>

GenerateResponse is the result from a `generate()` call and contains one or
more generated candidate messages.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `O` | `unknown` |

## Implements

- `GenerateResponseData`

## Constructors

### new GenerateResponse()

```ts
new GenerateResponse<O>(response: {
  "candidates": {
     "custom": unknown;
     "finishMessage": string;
     "finishReason":   | "length"
        | "unknown"
        | "stop"
        | "blocked"
        | "other";
     "index": number;
     "message": MessageSchema;
     "usage": {
        "custom": Record<string, number>;
        "inputCharacters": number;
        "inputImages": number;
        "inputTokens": number;
        "outputCharacters": number;
        "outputImages": number;
        "outputTokens": number;
        "totalTokens": number;
       };
    }[];
  "custom": unknown;
  "latencyMs": number;
  "request": {
     "candidates": number;
     "config": any;
     "context": {
        "content": ({
           "media": undefined;
           "text": string;
          } | {
           "media": {
              "contentType": ... | ...;
              "url": string;
             };
           "text": undefined;
          })[];
        "metadata": Record<string, any>;
       }[];
     "messages": {
        "content": (
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": string;
           "toolRequest": undefined;
           "toolResponse": undefined;
          }
           | {
           "data": unknown;
           "media": {
              "contentType": string;
              "url": string;
             };
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": undefined;
           "toolResponse": undefined;
          }
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": {
              "input": unknown;
              "name": string;
              "ref": string;
             };
           "toolResponse": undefined;
          }
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": undefined;
           "toolResponse": {
              "name": string;
              "output": unknown;
              "ref": string;
             };
          }
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": undefined;
           "toolResponse": undefined;
          })[];
        "role": RoleSchema;
       }[];
     "output": {
        "format": "text" | "media" | "json";
        "schema": Record<string, any>;
       };
     "tools": {
        "description": string;
        "inputSchema": Record<string, any>;
        "name": string;
        "outputSchema": Record<string, any>;
       }[];
    };
  "usage": {
     "custom": Record<string, number>;
     "inputCharacters": number;
     "inputImages": number;
     "inputTokens": number;
     "outputCharacters": number;
     "outputImages": number;
     "outputTokens": number;
     "totalTokens": number;
    };
}, request?: GenerateRequest<ZodTypeAny>): GenerateResponse<O>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `response` | `object` |
| `response.candidates` | \{ `"custom"`: `unknown`; `"finishMessage"`: `string`; `"finishReason"`: \| `"length"` \| `"unknown"` \| `"stop"` \| `"blocked"` \| `"other"`; `"index"`: `number`; `"message"`: `MessageSchema`; `"usage"`: \{ `"custom"`: `Record`\<`string`, `number`\>; `"inputCharacters"`: `number`; `"inputImages"`: `number`; `"inputTokens"`: `number`; `"outputCharacters"`: `number`; `"outputImages"`: `number`; `"outputTokens"`: `number`; `"totalTokens"`: `number`; \}; \}[] |
| `response.custom`? | `unknown` |
| `response.latencyMs`? | `number` |
| `response.request`? | `object` |
| `response.request.candidates`? | `number` |
| `response.request.config`? | `any` |
| `response.request.context`? | \{ `"content"`: (\{ `"media"`: `undefined`; `"text"`: `string`; \} \| \{ `"media"`: \{ `"contentType"`: ... \| ...; `"url"`: `string`; \}; `"text"`: `undefined`; \})[]; `"metadata"`: `Record`\<`string`, `any`\>; \}[] |
| `response.request.messages`? | \{ `"content"`: ( \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `string`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: \{ `"contentType"`: `string`; `"url"`: `string`; \}; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: \{ `"input"`: `unknown`; `"name"`: `string`; `"ref"`: `string`; \}; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: \{ `"name"`: `string`; `"output"`: `unknown`; `"ref"`: `string`; \}; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \})[]; `"role"`: `RoleSchema`; \}[] |
| `response.request.output`? | `object` |
| `response.request.output.format`? | `"text"` \| `"media"` \| `"json"` |
| `response.request.output.schema`? | `Record`\<`string`, `any`\> |
| `response.request.tools`? | \{ `"description"`: `string`; `"inputSchema"`: `Record`\<`string`, `any`\>; `"name"`: `string`; `"outputSchema"`: `Record`\<`string`, `any`\>; \}[] |
| `response.usage`? | `object` |
| `response.usage.custom`? | `Record`\<`string`, `number`\> |
| `response.usage.inputCharacters`? | `number` |
| `response.usage.inputImages`? | `number` |
| `response.usage.inputTokens`? | `number` |
| `response.usage.outputCharacters`? | `number` |
| `response.usage.outputImages`? | `number` |
| `response.usage.outputTokens`? | `number` |
| `response.usage.totalTokens`? | `number` |
| `request`? | `GenerateRequest`\<`ZodTypeAny`\> |

#### Returns

[`GenerateResponse`](GenerateResponse.md)\<`O`\>

#### Source

[ai/src/generate.ts:304](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L304)

## Properties

| Property | Type | Description |
| :------ | :------ | :------ |
| `candidates` | [`Candidate`](Candidate.md)\<`O`\>[] | The potential generated messages. |
| `custom` | `unknown` | Provider-specific response data. |
| `request?` | `GenerateRequest`\<`ZodTypeAny`\> | The request that generated this response. |
| `usage` | \{ `"custom"`: `Record`\<`string`, `number`\>; `"inputCharacters"`: `number`; `"inputImages"`: `number`; `"inputTokens"`: `number`; `"outputCharacters"`: `number`; `"outputImages"`: `number`; `"outputTokens"`: `number`; `"totalTokens"`: `number`; \} | Usage information. |
| `usage.custom?` | `Record`\<`string`, `number`\> | - |
| `usage.inputCharacters?` | `number` | - |
| `usage.inputImages?` | `number` | - |
| `usage.inputTokens?` | `number` | - |
| `usage.outputCharacters?` | `number` | - |
| `usage.outputImages?` | `number` | - |
| `usage.outputTokens?` | `number` | - |
| `usage.totalTokens?` | `number` | - |

## Methods

### data()

```ts
data(index: number): null | O
```

Returns the first detected `data` part of the selected candidate's message.

#### Parameters

| Parameter | Type | Default value | Description |
| :------ | :------ | :------ | :------ |
| `index` | `number` | `0` | The candidate index from which to extract data, defaults to first candidate. |

#### Returns

`null` \| `O`

The first `data` part detected in the candidate (if any).

#### Source

[ai/src/generate.ts:289](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L289)

***

### media()

```ts
media(index: number): null | {
  "contentType": string;
  "url": string;
}
```

Returns the first detected media part in the selected candidate's message. Useful for
extracting (for example) an image from a generation expected to create one.

#### Parameters

| Parameter | Type | Default value | Description |
| :------ | :------ | :------ | :------ |
| `index` | `number` | `0` | The candidate index from which to extract media, defaults to first candidate. |

#### Returns

`null` \| \{
  `"contentType"`: `string`;
  `"url"`: `string`;
 \}

The first detected `media` part in the candidate.

#### Source

[ai/src/generate.ts:280](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L280)

***

### output()

```ts
output(index?: number): null | O
```

If the selected candidate's message contains a `data` part, it is returned. Otherwise,
the `output()` method extracts the first valid JSON object or array from the text
contained in the selected candidate's message and returns it.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `index`? | `number` | The candidate index from which to extract output. If not provided, finds first candidate that conforms to output schema. |

#### Returns

`null` \| `O`

The structured output contained in the selected candidate.

#### Source

[ai/src/generate.ts:257](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L257)

***

### text()

```ts
text(index: number): string
```

Concatenates all `text` parts present in the candidate's message with no delimiter.

#### Parameters

| Parameter | Type | Default value | Description |
| :------ | :------ | :------ | :------ |
| `index` | `number` | `0` | The candidate index from which to extract text, defaults to first candidate. |

#### Returns

`string`

A string of all concatenated text parts.

#### Source

[ai/src/generate.ts:270](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L270)

***

### toHistory()

```ts
toHistory(index: number): {
  "content": (
     | {
     "data": unknown;
     "media": undefined;
     "metadata": Record<string, unknown>;
     "text": string;
     "toolRequest": undefined;
     "toolResponse": undefined;
    }
     | {
     "data": unknown;
     "media": {
        "contentType": string;
        "url": string;
       };
     "metadata": Record<string, unknown>;
     "text": undefined;
     "toolRequest": undefined;
     "toolResponse": undefined;
    }
     | {
     "data": unknown;
     "media": undefined;
     "metadata": Record<string, unknown>;
     "text": undefined;
     "toolRequest": {
        "input": unknown;
        "name": string;
        "ref": string;
       };
     "toolResponse": undefined;
    }
     | {
     "data": unknown;
     "media": undefined;
     "metadata": Record<string, unknown>;
     "text": undefined;
     "toolRequest": undefined;
     "toolResponse": {
        "name": string;
        "output": unknown;
        "ref": string;
       };
    }
     | {
     "data": unknown;
     "media": undefined;
     "metadata": Record<string, unknown>;
     "text": undefined;
     "toolRequest": undefined;
     "toolResponse": undefined;
    })[];
  "role": RoleSchema;
 }[]
```

Appends the message generated by the selected candidate to the messages already
present in the generation request. The result of this method can be safely
serialized to JSON for persistence in a database.

#### Parameters

| Parameter | Type | Default value | Description |
| :------ | :------ | :------ | :------ |
| `index` | `number` | `0` | The candidate index to utilize during conversion, defaults to first candidate. |

#### Returns

\{
  `"content"`: (
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `string`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: `undefined`;
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: \{
        `"contentType"`: `string`;
        `"url"`: `string`;
       \};
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: `undefined`;
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: \{
        `"input"`: `unknown`;
        `"name"`: `string`;
        `"ref"`: `string`;
       \};
     `"toolResponse"`: `undefined`;
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: \{
        `"name"`: `string`;
        `"output"`: `unknown`;
        `"ref"`: `string`;
       \};
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: `undefined`;
    \})[];
  `"role"`: `RoleSchema`;
 \}[]

A serializable list of messages compatible with `generate({history})`.

#### Source

[ai/src/generate.ts:300](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L300)

***

### toJSON()

```ts
toJSON(): {
  "candidates": {
     "custom": unknown;
     "finishMessage": string;
     "finishReason":   | "length"
        | "unknown"
        | "stop"
        | "blocked"
        | "other";
     "index": number;
     "message": MessageSchema;
     "usage": {
        "custom": Record<string, number>;
        "inputCharacters": number;
        "inputImages": number;
        "inputTokens": number;
        "outputCharacters": number;
        "outputImages": number;
        "outputTokens": number;
        "totalTokens": number;
       };
    }[];
  "custom": unknown;
  "latencyMs": number;
  "request": {
     "candidates": number;
     "config": any;
     "context": {
        "content": ({
           "media": undefined;
           "text": string;
          } | {
           "media": {
              "contentType": ... | ...;
              "url": string;
             };
           "text": undefined;
          })[];
        "metadata": Record<string, any>;
       }[];
     "messages": {
        "content": (
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": string;
           "toolRequest": undefined;
           "toolResponse": undefined;
          }
           | {
           "data": unknown;
           "media": {
              "contentType": string;
              "url": string;
             };
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": undefined;
           "toolResponse": undefined;
          }
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": {
              "input": unknown;
              "name": string;
              "ref": string;
             };
           "toolResponse": undefined;
          }
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": undefined;
           "toolResponse": {
              "name": string;
              "output": unknown;
              "ref": string;
             };
          }
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": undefined;
           "toolResponse": undefined;
          })[];
        "role": RoleSchema;
       }[];
     "output": {
        "format": "text" | "media" | "json";
        "schema": Record<string, any>;
       };
     "tools": {
        "description": string;
        "inputSchema": Record<string, any>;
        "name": string;
        "outputSchema": Record<string, any>;
       }[];
    };
  "usage": {
     "custom": Record<string, number>;
     "inputCharacters": number;
     "inputImages": number;
     "inputTokens": number;
     "outputCharacters": number;
     "outputImages": number;
     "outputTokens": number;
     "totalTokens": number;
    };
}
```

#### Returns

```ts
{
  "candidates": {
     "custom": unknown;
     "finishMessage": string;
     "finishReason":   | "length"
        | "unknown"
        | "stop"
        | "blocked"
        | "other";
     "index": number;
     "message": MessageSchema;
     "usage": {
        "custom": Record<string, number>;
        "inputCharacters": number;
        "inputImages": number;
        "inputTokens": number;
        "outputCharacters": number;
        "outputImages": number;
        "outputTokens": number;
        "totalTokens": number;
       };
    }[];
  "custom": unknown;
  "latencyMs": number;
  "request": {
     "candidates": number;
     "config": any;
     "context": {
        "content": ({
           "media": undefined;
           "text": string;
          } | {
           "media": {
              "contentType": ... | ...;
              "url": string;
             };
           "text": undefined;
          })[];
        "metadata": Record<string, any>;
       }[];
     "messages": {
        "content": (
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": string;
           "toolRequest": undefined;
           "toolResponse": undefined;
          }
           | {
           "data": unknown;
           "media": {
              "contentType": string;
              "url": string;
             };
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": undefined;
           "toolResponse": undefined;
          }
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": {
              "input": unknown;
              "name": string;
              "ref": string;
             };
           "toolResponse": undefined;
          }
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": undefined;
           "toolResponse": {
              "name": string;
              "output": unknown;
              "ref": string;
             };
          }
           | {
           "data": unknown;
           "media": undefined;
           "metadata": Record<string, unknown>;
           "text": undefined;
           "toolRequest": undefined;
           "toolResponse": undefined;
          })[];
        "role": RoleSchema;
       }[];
     "output": {
        "format": "text" | "media" | "json";
        "schema": Record<string, any>;
       };
     "tools": {
        "description": string;
        "inputSchema": Record<string, any>;
        "name": string;
        "outputSchema": Record<string, any>;
       }[];
    };
  "usage": {
     "custom": Record<string, number>;
     "inputCharacters": number;
     "inputImages": number;
     "inputTokens": number;
     "outputCharacters": number;
     "outputImages": number;
     "outputTokens": number;
     "totalTokens": number;
    };
}
```

| Member | Type | Value |
| :------ | :------ | :------ |
| `candidates` | \{
  `"custom"`: `unknown`;
  `"finishMessage"`: `string`;
  `"finishReason"`:   \| `"length"`
     \| `"unknown"`
     \| `"stop"`
     \| `"blocked"`
     \| `"other"`;
  `"index"`: `number`;
  `"message"`: `MessageSchema`;
  `"usage"`: \{
     `"custom"`: `Record`\<`string`, `number`\>;
     `"inputCharacters"`: `number`;
     `"inputImages"`: `number`;
     `"inputTokens"`: `number`;
     `"outputCharacters"`: `number`;
     `"outputImages"`: `number`;
     `"outputTokens"`: `number`;
     `"totalTokens"`: `number`;
    \};
 \}[] | ... |
| `custom` | `unknown` | ... |
| `latencyMs` | `number` | ... |
| `request` | \{
  `"candidates"`: `number`;
  `"config"`: `any`;
  `"context"`: \{
     `"content"`: (\{
        `"media"`: `undefined`;
        `"text"`: `string`;
       \} \| \{
        `"media"`: \{
           `"contentType"`: ... \| ...;
           `"url"`: `string`;
          \};
        `"text"`: `undefined`;
       \})[];
     `"metadata"`: `Record`\<`string`, `any`\>;
    \}[];
  `"messages"`: \{
     `"content"`: (
        \| \{
        `"data"`: `unknown`;
        `"media"`: `undefined`;
        `"metadata"`: `Record`\<`string`, `unknown`\>;
        `"text"`: `string`;
        `"toolRequest"`: `undefined`;
        `"toolResponse"`: `undefined`;
       \}
        \| \{
        `"data"`: `unknown`;
        `"media"`: \{
           `"contentType"`: `string`;
           `"url"`: `string`;
          \};
        `"metadata"`: `Record`\<`string`, `unknown`\>;
        `"text"`: `undefined`;
        `"toolRequest"`: `undefined`;
        `"toolResponse"`: `undefined`;
       \}
        \| \{
        `"data"`: `unknown`;
        `"media"`: `undefined`;
        `"metadata"`: `Record`\<`string`, `unknown`\>;
        `"text"`: `undefined`;
        `"toolRequest"`: \{
           `"input"`: `unknown`;
           `"name"`: `string`;
           `"ref"`: `string`;
          \};
        `"toolResponse"`: `undefined`;
       \}
        \| \{
        `"data"`: `unknown`;
        `"media"`: `undefined`;
        `"metadata"`: `Record`\<`string`, `unknown`\>;
        `"text"`: `undefined`;
        `"toolRequest"`: `undefined`;
        `"toolResponse"`: \{
           `"name"`: `string`;
           `"output"`: `unknown`;
           `"ref"`: `string`;
          \};
       \}
        \| \{
        `"data"`: `unknown`;
        `"media"`: `undefined`;
        `"metadata"`: `Record`\<`string`, `unknown`\>;
        `"text"`: `undefined`;
        `"toolRequest"`: `undefined`;
        `"toolResponse"`: `undefined`;
       \})[];
     `"role"`: `RoleSchema`;
    \}[];
  `"output"`: \{
     `"format"`: `"text"` \| `"media"` \| `"json"`;
     `"schema"`: `Record`\<`string`, `any`\>;
    \};
  `"tools"`: \{
     `"description"`: `string`;
     `"inputSchema"`: `Record`\<`string`, `any`\>;
     `"name"`: `string`;
     `"outputSchema"`: `Record`\<`string`, `any`\>;
    \}[];
 \} | ... |
| `request.candidates` | `number` | ... |
| `request.config` | `any` | ... |
| `request.context` | \{
  `"content"`: (\{
     `"media"`: `undefined`;
     `"text"`: `string`;
    \} \| \{
     `"media"`: \{
        `"contentType"`: ... \| ...;
        `"url"`: `string`;
       \};
     `"text"`: `undefined`;
    \})[];
  `"metadata"`: `Record`\<`string`, `any`\>;
 \}[] | ... |
| `request.messages` | \{
  `"content"`: (
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `string`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: `undefined`;
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: \{
        `"contentType"`: `string`;
        `"url"`: `string`;
       \};
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: `undefined`;
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: \{
        `"input"`: `unknown`;
        `"name"`: `string`;
        `"ref"`: `string`;
       \};
     `"toolResponse"`: `undefined`;
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: \{
        `"name"`: `string`;
        `"output"`: `unknown`;
        `"ref"`: `string`;
       \};
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: `undefined`;
    \})[];
  `"role"`: `RoleSchema`;
 \}[] | ... |
| `request.output` | \{
  `"format"`: `"text"` \| `"media"` \| `"json"`;
  `"schema"`: `Record`\<`string`, `any`\>;
 \} | ... |
| `request.output.format` | `"text"` \| `"media"` \| `"json"` | ... |
| `request.output.schema` | `Record`\<`string`, `any`\> | ... |
| `request.tools` | \{
  `"description"`: `string`;
  `"inputSchema"`: `Record`\<`string`, `any`\>;
  `"name"`: `string`;
  `"outputSchema"`: `Record`\<`string`, `any`\>;
 \}[] | ... |
| `usage` | \{
  `"custom"`: `Record`\<`string`, `number`\>;
  `"inputCharacters"`: `number`;
  `"inputImages"`: `number`;
  `"inputTokens"`: `number`;
  `"outputCharacters"`: `number`;
  `"outputImages"`: `number`;
  `"outputTokens"`: `number`;
  `"totalTokens"`: `number`;
 \} | ... |
| `usage.custom` | `Record`\<`string`, `number`\> | ... |
| `usage.inputCharacters` | `number` | ... |
| `usage.inputImages` | `number` | ... |
| `usage.inputTokens` | `number` | ... |
| `usage.outputCharacters` | `number` | ... |
| `usage.outputImages` | `number` | ... |
| `usage.outputTokens` | `number` | ... |
| `usage.totalTokens` | `number` | ... |

#### Source

[ai/src/generate.ts:313](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L313)
