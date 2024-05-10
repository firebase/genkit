# Class: Message\<T\>

Message represents a single role's contribution to a generation. Each message
can contain multiple parts (for example text and an image), and each generation
can contain multiple messages.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `T` | `unknown` |

## Implements

- `MessageData`

## Constructors

### new Message()

```ts
new Message<T>(message: {
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
}): Message<T>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `message` | `object` |
| `message.content` | ( \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `string`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: \{ `"contentType"`: `string`; `"url"`: `string`; \}; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: \{ `"input"`: `unknown`; `"name"`: `string`; `"ref"`: `string`; \}; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: \{ `"name"`: `string`; `"output"`: `unknown`; `"ref"`: `string`; \}; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \})[] |
| `message.role` | `"model"` \| `"tool"` \| `"system"` \| `"user"` |

#### Returns

[`Message`](Message.md)\<`T`\>

#### Source

[ai/src/generate.ts:61](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L61)

## Properties

| Property | Type |
| :------ | :------ |
| `content` | ( \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `string`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: \{ `"contentType"`: `string`; `"url"`: `string`; \}; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: \{ `"input"`: `unknown`; `"name"`: `string`; `"ref"`: `string`; \}; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: \{ `"name"`: `string`; `"output"`: `unknown`; `"ref"`: `string`; \}; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \})[] |
| `role` | `"model"` \| `"tool"` \| `"system"` \| `"user"` |

## Methods

### data()

```ts
data(): null | T
```

Returns the first detected `data` part of a message.

#### Returns

`null` \| `T`

The first `data` part detected in the message (if any).

#### Source

[ai/src/generate.ts:103](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L103)

***

### media()

```ts
media(): null | {
  "contentType": string;
  "url": string;
}
```

Returns the first media part detected in the message. Useful for extracting
(for example) an image from a generation expected to create one.

#### Returns

`null` \| \{
  `"contentType"`: `string`;
  `"url"`: `string`;
 \}

The first detected `media` part in the message.

#### Source

[ai/src/generate.ts:95](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L95)

***

### output()

```ts
output(): null | T
```

If a message contains a `data` part, it is returned. Otherwise, the `output()`
method extracts the first valid JSON object or array from the text contained in
the message and returns it.

#### Returns

`null` \| `T`

The structured output contained in the message.

#### Source

[ai/src/generate.ts:73](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L73)

***

### text()

```ts
text(): string
```

Concatenates all `text` parts present in the message with no delimiter.

#### Returns

`string`

A string of all concatenated text parts.

#### Source

[ai/src/generate.ts:86](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L86)

***

### toJSON()

```ts
toJSON(): {
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
}
```

Converts the Message to a plain JS object.

#### Returns

```ts
{
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
}
```

Plain JS object representing the data contained in the message.

| Member | Type | Value |
| :------ | :------ | :------ |
| `content` | (
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
| `role` | `"model"` \| `"tool"` \| `"system"` \| `"user"` | RoleSchema |

#### Source

[ai/src/generate.ts:111](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L111)

***

### toolResponseParts()

```ts
toolResponseParts(): {
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
 }[]
```

#### Returns

\{
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
 \}[]

#### Source

[ai/src/generate.ts:77](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/generate.ts#L77)
