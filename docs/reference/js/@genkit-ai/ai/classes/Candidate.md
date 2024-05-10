# Class: Candidate\<O\>

Candidate represents one of several possible generated responses from a generation
request. A candidate contains a single generated message along with additional
metadata about its generation. A generation request can create multiple candidates.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `O` | `unknown` |

## Implements

- `CandidateData`

## Constructors

### new Candidate()

```ts
new Candidate<O>(candidate: {
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
}, request?: GenerateRequest<ZodTypeAny>): Candidate<O>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `candidate` | `object` |
| `candidate.custom`? | `unknown` |
| `candidate.finishMessage`? | `string` |
| `candidate.finishReason`? |  \| `"length"` \| `"unknown"` \| `"stop"` \| `"blocked"` \| `"other"` |
| `candidate.index`? | `number` |
| `candidate.message`? | `object` |
| `candidate.message.content`? | ( \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `string`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: \{ `"contentType"`: `string`; `"url"`: `string`; \}; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: \{ `"input"`: `unknown`; `"name"`: `string`; `"ref"`: `string`; \}; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: \{ `"name"`: `string`; `"output"`: `unknown`; `"ref"`: `string`; \}; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \})[] |
| `candidate.message.role`? | `"model"` \| `"tool"` \| `"system"` \| `"user"` |
| `candidate.usage`? | `object` |
| `candidate.usage.custom`? | `Record`\<`string`, `number`\> |
| `candidate.usage.inputCharacters`? | `number` |
| `candidate.usage.inputImages`? | `number` |
| `candidate.usage.inputTokens`? | `number` |
| `candidate.usage.outputCharacters`? | `number` |
| `candidate.usage.outputImages`? | `number` |
| `candidate.usage.outputTokens`? | `number` |
| `candidate.usage.totalTokens`? | `number` |
| `request`? | `GenerateRequest`\<`ZodTypeAny`\> |

#### Returns

[`Candidate`](Candidate.md)\<`O`\>

#### Source

[ai/src/generate.ts:140](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L140)

## Properties

| Property | Type | Description |
| :------ | :------ | :------ |
| `custom` | `unknown` | Additional provider-specific information about this candidate. |
| `finishMessage?` | `string` | Additional information about why the candidate stopped generating, if any. |
| `finishReason` |  \| `"length"` \| `"unknown"` \| `"stop"` \| `"blocked"` \| `"other"` | The reason generation stopped for this candidate. |
| `index` | `number` | The positional index of this candidate in the generation response. |
| `message` | [`Message`](Message.md)\<`O`\> | The message this candidate generated. |
| `request?` | `GenerateRequest`\<`ZodTypeAny`\> | The request that led to the generation of this candidate. |
| `usage` | \{ `"custom"`: `Record`\<`string`, `number`\>; `"inputCharacters"`: `number`; `"inputImages"`: `number`; `"inputTokens"`: `number`; `"outputCharacters"`: `number`; `"outputImages"`: `number`; `"outputTokens"`: `number`; `"totalTokens"`: `number`; \} | Usage information about this candidate. |
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
data(): null | O
```

Returns the first detected `data` part of a candidate's message.

#### Returns

`null` \| `O`

The first `data` part detected in the candidate (if any).

#### Source

[ai/src/generate.ts:182](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L182)

***

### hasValidOutput()

```ts
hasValidOutput(request?: GenerateRequest<ZodTypeAny>): boolean
```

Determine whether this candidate has output that conforms to a provided schema.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `request`? | `GenerateRequest`\<`ZodTypeAny`\> | A request containing output schema to validate against. If not provided, uses request embedded in candidate. |

#### Returns

`boolean`

True if output matches request schema or if no request schema is provided.

#### Source

[ai/src/generate.ts:192](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L192)

***

### media()

```ts
media(): null | {
  "contentType": string;
  "url": string;
}
```

Returns the first detected media part in the candidate's message. Useful for extracting
(for example) an image from a generation expected to create one.

#### Returns

`null` \| \{
  `"contentType"`: `string`;
  `"url"`: `string`;
 \}

The first detected `media` part in the candidate.

#### Source

[ai/src/generate.ts:174](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L174)

***

### output()

```ts
output(): null | O
```

If a candidate's message contains a `data` part, it is returned. Otherwise, the `output()`
method extracts the first valid JSON object or array from the text contained in
the candidate's message and returns it.

#### Returns

`null` \| `O`

The structured output contained in the candidate.

#### Source

[ai/src/generate.ts:157](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L157)

***

### text()

```ts
text(): string
```

Concatenates all `text` parts present in the candidate's message with no delimiter.

#### Returns

`string`

A string of all concatenated text parts.

#### Source

[ai/src/generate.ts:165](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L165)

***

### toHistory()

```ts
toHistory(): {
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

Appends the message generated by this candidate to the messages already
present in the generation request. The result of this method can be safely
serialized to JSON for persistence in a database.

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

[ai/src/generate.ts:209](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L209)

***

### toJSON()

```ts
toJSON(): {
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
}
```

Converts the Candidate to a plain JS object.

#### Returns

```ts
{
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
}
```

Plain JS object representing the data contained in the candidate.

| Member | Type | Value |
| :------ | :------ | :------ |
| `custom` | `unknown` | ... |
| `finishMessage` | `string` | ... |
| `finishReason` | 
  \| `"length"`
  \| `"unknown"`
  \| `"stop"`
  \| `"blocked"`
  \| `"other"` | ... |
| `index` | `number` | ... |
| `message` | \{
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
 \} | MessageSchema |
| `message.content` | (
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
 \})[] | ... |
| `message.role` | `"model"` \| `"tool"` \| `"system"` \| `"user"` | RoleSchema |
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

[ai/src/generate.ts:221](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L221)
