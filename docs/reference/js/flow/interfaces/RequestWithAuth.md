# Interface: \_\_RequestWithAuth

For express-based flows, req.auth should contain the value to bepassed into
the flow context.

## Extends

- `Request`

## Properties

| Property | Modifier | Flags | Type | Description | Inherited from |
| :------ | :------ | :------ | :------ | :------ | :------ |
| ~~`aborted`~~ | `public` |  | `boolean` | The `message.aborted` property will be `true` if the request has<br />been aborted.<br /><br />**Since**<br />v10.1.0<br /><br />**Deprecated**<br />Since v17.0.0,v16.12.0 - Check `message.destroyed` from <a href="stream.html#class-streamreadable" class="type">stream.Readable</a>. | `express.Request.aborted` |
| `accepted` | `public` |  | `MediaType`[] | Return an array of Accepted media types<br />ordered from highest quality to lowest. | `express.Request.accepted` |
| `app` | `public` |  | `Application`\<`Record`\<`string`, `any`\>\> | - | `express.Request.app` |
| `auth?` | `public` |  | `unknown` | - | - |
| `baseUrl` | `public` |  | `string` | - | `express.Request.baseUrl` |
| `body` | `public` |  | `any` | - | `express.Request.body` |
| `closed` | `readonly` |  | `boolean` | Is `true` after `'close'` has been emitted.<br /><br />**Since**<br />v18.0.0 | `express.Request.closed` |
| `complete` | `public` |  | `boolean` | The `message.complete` property will be `true` if a complete HTTP message has<br />been received and successfully parsed.<br /><br />This property is particularly useful as a means of determining if a client or<br />server fully transmitted a message before a connection was terminated:<br /><br />`jsconst req = http.request({  host: '127.0.0.1',  port: 8080,  method: 'POST',}, (res) => {  res.resume();  res.on('end', () => {    if (!res.complete)      console.error(        'The connection was terminated while the message was still being sent');  });});`<br /><br />**Since**<br />v0.3.0 | `express.Request.complete` |
| ~~`connection`~~ | `public` |  | `Socket` | Alias for `message.socket`.<br /><br />**Since**<br />v0.1.90<br /><br />**Deprecated**<br />Since v16.0.0 - Use `socket`. | `express.Request.connection` |
| `cookies` | `public` |  | `any` | - | `express.Request.cookies` |
| `destroyed` | `public` |  | `boolean` | Is `true` after `readable.destroy()` has been called.<br /><br />**Since**<br />v8.0.0 | `express.Request.destroyed` |
| `errored` | `readonly` |  | `null` \| `Error` | Returns error if the stream has been destroyed with an error.<br /><br />**Since**<br />v18.0.0 | `express.Request.errored` |
| `fresh` | `public` |  | `boolean` | Check if the request is fresh, aka<br />Last-Modified and/or the ETag<br />still match. | `express.Request.fresh` |
| `headers` | `public` |  | `IncomingHttpHeaders` | The request/response headers object.<br /><br />Key-value pairs of header names and values. Header names are lower-cased.<br /><br />`js// Prints something like://// { 'user-agent': 'curl/7.22.0',//   host: '127.0.0.1:8000',//   accept: '*' }console.log(request.headers);`<br /><br />Duplicates in raw headers are handled in the following ways, depending on the<br />header name:<br /><br />* Duplicates of `age`, `authorization`, `content-length`, `content-type`,`etag`, `expires`, `from`, `host`, `if-modified-since`, `if-unmodified-since`,`last-modified`, `location`,<br />`max-forwards`, `proxy-authorization`, `referer`,`retry-after`, `server`, or `user-agent` are discarded.<br />To allow duplicate values of the headers listed above to be joined,<br />use the option `joinDuplicateHeaders` in request and createServer. See RFC 9110 Section 5.3 for more<br />information.<br />* `set-cookie` is always an array. Duplicates are added to the array.<br />* For duplicate `cookie` headers, the values are joined together with `; `.<br />* For all other headers, the values are joined together with `, `.<br /><br />**Since**<br />v0.1.5 | `express.Request.headers` |
| `headersDistinct` | `public` |  | `Dict`\<`string`[]\> | Similar to `message.headers`, but there is no join logic and the values are<br />always arrays of strings, even for headers received just once.<br /><br />`js// Prints something like://// { 'user-agent': ['curl/7.22.0'],//   host: ['127.0.0.1:8000'],//   accept: ['*'] }console.log(request.headersDistinct);`<br /><br />**Since**<br />v18.3.0, v16.17.0 | `express.Request.headersDistinct` |
| ~~`host`~~ | `public` |  | `string` | **Deprecated**<br />Use hostname instead. | `express.Request.host` |
| `hostname` | `public` |  | `string` | Parse the "Host" header field hostname. | `express.Request.hostname` |
| `httpVersion` | `public` |  | `string` | In case of server request, the HTTP version sent by the client. In the case of<br />client response, the HTTP version of the connected-to server.<br />Probably either `'1.1'` or `'1.0'`.<br /><br />Also `message.httpVersionMajor` is the first integer and`message.httpVersionMinor` is the second.<br /><br />**Since**<br />v0.1.1 | `express.Request.httpVersion` |
| `httpVersionMajor` | `public` |  | `number` | - | `express.Request.httpVersionMajor` |
| `httpVersionMinor` | `public` |  | `number` | - | `express.Request.httpVersionMinor` |
| `ip` | `public` |  | `undefined` \| `string` | Return the remote address, or when<br />"trust proxy" is `true` return<br />the upstream addr.<br /><br />Value may be undefined if the `req.socket` is destroyed<br />(for example, if the client disconnected). | `express.Request.ip` |
| `ips` | `public` |  | `string`[] | When "trust proxy" is `true`, parse<br />the "X-Forwarded-For" ip address list.<br /><br />For example if the value were "client, proxy1, proxy2"<br />you would receive the array `["client", "proxy1", "proxy2"]`<br />where "proxy2" is the furthest down-stream. | `express.Request.ips` |
| `method` | `public` |  | `string` | - | `express.Request.method` |
| `next?` | `public` |  | `NextFunction` | - | `express.Request.next` |
| `originalUrl` | `public` |  | `string` | - | `express.Request.originalUrl` |
| `params` | `public` |  | `ParamsDictionary` | - | `express.Request.params` |
| `path` | `public` |  | `string` | Short-hand for `url.parse(req.url).pathname`. | `express.Request.path` |
| `protocol` | `public` |  | `string` | Return the protocol string "http" or "https"<br />when requested with TLS. When the "trust proxy"<br />setting is enabled the "X-Forwarded-Proto" header<br />field will be trusted. If you're running behind<br />a reverse proxy that supplies https for you this<br />may be enabled. | `express.Request.protocol` |
| `query` | `public` |  | `ParsedQs` | - | `express.Request.query` |
| `rawHeaders` | `public` |  | `string`[] | The raw request/response headers list exactly as they were received.<br /><br />The keys and values are in the same list. It is _not_ a<br />list of tuples. So, the even-numbered offsets are key values, and the<br />odd-numbered offsets are the associated values.<br /><br />Header names are not lowercased, and duplicates are not merged.<br /><br />`js// Prints something like://// [ 'user-agent',//   'this is invalid because there can be only one',//   'User-Agent',//   'curl/7.22.0',//   'Host',//   '127.0.0.1:8000',//   'ACCEPT',//   '*' ]console.log(request.rawHeaders);`<br /><br />**Since**<br />v0.11.6 | `express.Request.rawHeaders` |
| `rawTrailers` | `public` |  | `string`[] | The raw request/response trailer keys and values exactly as they were<br />received. Only populated at the `'end'` event.<br /><br />**Since**<br />v0.11.6 | `express.Request.rawTrailers` |
| `readable` | `public` |  | `boolean` | Is `true` if it is safe to call `readable.read()`, which means<br />the stream has not been destroyed or emitted `'error'` or `'end'`.<br /><br />**Since**<br />v11.4.0 | `express.Request.readable` |
| `readableAborted` | `readonly` | `Experimental` | `boolean` | Returns whether the stream was destroyed or errored before emitting `'end'`.<br /><br />**Since**<br />v16.8.0 | `express.Request.readableAborted` |
| `readableDidRead` | `readonly` | `Experimental` | `boolean` | Returns whether `'data'` has been emitted.<br /><br />**Since**<br />v16.7.0, v14.18.0 | `express.Request.readableDidRead` |
| `readableEncoding` | `readonly` |  | `null` \| `BufferEncoding` | Getter for the property `encoding` of a given `Readable` stream. The `encoding`property can be set using the `readable.setEncoding()` method.<br /><br />**Since**<br />v12.7.0 | `express.Request.readableEncoding` |
| `readableEnded` | `readonly` |  | `boolean` | Becomes `true` when `'end'` event is emitted.<br /><br />**Since**<br />v12.9.0 | `express.Request.readableEnded` |
| `readableFlowing` | `readonly` |  | `null` \| `boolean` | This property reflects the current state of a `Readable` stream as described<br />in the `Three states` section.<br /><br />**Since**<br />v9.4.0 | `express.Request.readableFlowing` |
| `readableHighWaterMark` | `readonly` |  | `number` | Returns the value of `highWaterMark` passed when creating this `Readable`.<br /><br />**Since**<br />v9.3.0 | `express.Request.readableHighWaterMark` |
| `readableLength` | `readonly` |  | `number` | This property contains the number of bytes (or objects) in the queue<br />ready to be read. The value provides introspection data regarding<br />the status of the `highWaterMark`.<br /><br />**Since**<br />v9.4.0 | `express.Request.readableLength` |
| `readableObjectMode` | `readonly` |  | `boolean` | Getter for the property `objectMode` of a given `Readable` stream.<br /><br />**Since**<br />v12.3.0 | `express.Request.readableObjectMode` |
| `res?` | `public` |  | `Response`\<`any`, `Record`\<`string`, `any`\>, `number`\> | After middleware.init executed, Request will contain res and next properties<br />See: express/lib/middleware/init.js | `express.Request.res` |
| `route` | `public` |  | `any` | - | `express.Request.route` |
| `secure` | `public` |  | `boolean` | Short-hand for:<br /><br />   req.protocol == 'https' | `express.Request.secure` |
| `signedCookies` | `public` |  | `any` | - | `express.Request.signedCookies` |
| `socket` | `public` |  | `Socket` | The `net.Socket` object associated with the connection.<br /><br />With HTTPS support, use `request.socket.getPeerCertificate()` to obtain the<br />client's authentication details.<br /><br />This property is guaranteed to be an instance of the `net.Socket` class,<br />a subclass of `stream.Duplex`, unless the user specified a socket<br />type other than `net.Socket` or internally nulled.<br /><br />**Since**<br />v0.3.0 | `express.Request.socket` |
| `stale` | `public` |  | `boolean` | Check if the request is stale, aka<br />"Last-Modified" and / or the "ETag" for the<br />resource has changed. | `express.Request.stale` |
| `statusCode?` | `public` |  | `number` | **Only valid for response obtained from ClientRequest.**<br /><br />The 3-digit HTTP response status code. E.G. `404`.<br /><br />**Since**<br />v0.1.1 | `express.Request.statusCode` |
| `statusMessage?` | `public` |  | `string` | **Only valid for response obtained from ClientRequest.**<br /><br />The HTTP response status message (reason phrase). E.G. `OK` or `Internal Server Error`.<br /><br />**Since**<br />v0.11.10 | `express.Request.statusMessage` |
| `subdomains` | `public` |  | `string`[] | Return subdomains as an array.<br /><br />Subdomains are the dot-separated parts of the host before the main domain of<br />the app. By default, the domain of the app is assumed to be the last two<br />parts of the host. This can be changed by setting "subdomain offset".<br /><br />For example, if the domain is "tobi.ferrets.example.com":<br />If "subdomain offset" is not set, req.subdomains is `["ferrets", "tobi"]`.<br />If "subdomain offset" is 3, req.subdomains is `["tobi"]`. | `express.Request.subdomains` |
| `trailers` | `public` |  | `Dict`\<`string`\> | The request/response trailers object. Only populated at the `'end'` event.<br /><br />**Since**<br />v0.3.0 | `express.Request.trailers` |
| `trailersDistinct` | `public` |  | `Dict`\<`string`[]\> | Similar to `message.trailers`, but there is no join logic and the values are<br />always arrays of strings, even for headers received just once.<br />Only populated at the `'end'` event.<br /><br />**Since**<br />v18.3.0, v16.17.0 | `express.Request.trailersDistinct` |
| `url` | `public` |  | `string` | - | `express.Request.url` |
| `xhr` | `public` |  | `boolean` | Check if the request was an _XMLHttpRequest_. | `express.Request.xhr` |

## Methods

### `[asyncDispose]`()

```ts
asyncDispose: Promise<void>
```

Calls `readable.destroy()` with an `AbortError` and returns a promise that fulfills when the stream is finished.

#### Returns

`Promise`\<`void`\>

#### Inherited from

`express.Request.[asyncDispose]`

#### Since

v20.4.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:651

***

### `[asyncIterator]`()

```ts
asyncIterator: AsyncIterableIterator<any>
```

#### Returns

`AsyncIterableIterator`\<`any`\>

#### Inherited from

`express.Request.[asyncIterator]`

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:646

***

### `[captureRejectionSymbol]`()?

```ts
optional [captureRejectionSymbol]<K>(
   error: Error, 
   event: string | symbol, ...
   args: AnyRest): void
```

#### Type parameters

| Type parameter |
| :------ |
| `K` |

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `error` | `Error` |
| `event` | `string` \| `symbol` |
| ...`args` | `AnyRest` |

#### Returns

`void`

#### Inherited from

`express.Request.[captureRejectionSymbol]`

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/events.d.ts:129

***

### \_construct()?

```ts
optional _construct(callback: (error?: null | Error) => void): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `callback` | (`error`?: `null` \| `Error`) => `void` |

#### Returns

`void`

#### Inherited from

`express.Request._construct`

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:126

***

### \_destroy()

```ts
_destroy(error: null | Error, callback: (error?: null | Error) => void): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `error` | `null` \| `Error` |
| `callback` | (`error`?: `null` \| `Error`) => `void` |

#### Returns

`void`

#### Inherited from

`express.Request._destroy`

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:566

***

### \_read()

```ts
_read(size: number): void
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `size` | `number` |

#### Returns

`void`

#### Inherited from

`express.Request._read`

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:127

***

### accepts()

#### accepts(undefined)

```ts
accepts(): string[]
```

Check if the given `type(s)` is acceptable, returning
the best match when true, otherwise `undefined`, in which
case you should respond with 406 "Not Acceptable".

The `type` value may be a single mime type string
such as "application/json", the extension name
such as "json", a comma-delimted list such as "json, html, text/plain",
or an array `["json", "html", "text/plain"]`. When a list
or array is given the _best_ match, if any is returned.

Examples:

    // Accept: text/html
    req.accepts('html');
    // => "html"

    // Accept: text/*, application/json
    req.accepts('html');
    // => "html"
    req.accepts('text/html');
    // => "text/html"
    req.accepts('json, text');
    // => "json"
    req.accepts('application/json');
    // => "application/json"

    // Accept: text/*, application/json
    req.accepts('image/png');
    req.accepts('png');
    // => false

    // Accept: text/*;q=.5, application/json
    req.accepts(['html', 'json']);
    req.accepts('html, json');
    // => "json"

##### Returns

`string`[]

##### Inherited from

`express.Request.accepts`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:454

#### accepts(type)

```ts
accepts(type: string): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `type` | `string` |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.accepts`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:455

#### accepts(type)

```ts
accepts(type: string[]): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `type` | `string`[] |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.accepts`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:456

#### accepts(type)

```ts
accepts(...type: string[]): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| ...`type` | `string`[] |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.accepts`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:457

***

### acceptsCharsets()

#### acceptsCharsets(undefined)

```ts
acceptsCharsets(): string[]
```

Returns the first accepted charset of the specified character sets,
based on the request's Accept-Charset HTTP header field.
If none of the specified charsets is accepted, returns false.

For more information, or if you have issues or concerns, see accepts.

##### Returns

`string`[]

##### Inherited from

`express.Request.acceptsCharsets`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:466

#### acceptsCharsets(charset)

```ts
acceptsCharsets(charset: string): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `charset` | `string` |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.acceptsCharsets`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:467

#### acceptsCharsets(charset)

```ts
acceptsCharsets(charset: string[]): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `charset` | `string`[] |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.acceptsCharsets`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:468

#### acceptsCharsets(charset)

```ts
acceptsCharsets(...charset: string[]): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| ...`charset` | `string`[] |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.acceptsCharsets`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:469

***

### acceptsEncodings()

#### acceptsEncodings(undefined)

```ts
acceptsEncodings(): string[]
```

Returns the first accepted encoding of the specified encodings,
based on the request's Accept-Encoding HTTP header field.
If none of the specified encodings is accepted, returns false.

For more information, or if you have issues or concerns, see accepts.

##### Returns

`string`[]

##### Inherited from

`express.Request.acceptsEncodings`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:478

#### acceptsEncodings(encoding)

```ts
acceptsEncodings(encoding: string): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `encoding` | `string` |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.acceptsEncodings`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:479

#### acceptsEncodings(encoding)

```ts
acceptsEncodings(encoding: string[]): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `encoding` | `string`[] |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.acceptsEncodings`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:480

#### acceptsEncodings(encoding)

```ts
acceptsEncodings(...encoding: string[]): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| ...`encoding` | `string`[] |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.acceptsEncodings`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:481

***

### acceptsLanguages()

#### acceptsLanguages(undefined)

```ts
acceptsLanguages(): string[]
```

Returns the first accepted language of the specified languages,
based on the request's Accept-Language HTTP header field.
If none of the specified languages is accepted, returns false.

For more information, or if you have issues or concerns, see accepts.

##### Returns

`string`[]

##### Inherited from

`express.Request.acceptsLanguages`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:490

#### acceptsLanguages(lang)

```ts
acceptsLanguages(lang: string): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `lang` | `string` |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.acceptsLanguages`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:491

#### acceptsLanguages(lang)

```ts
acceptsLanguages(lang: string[]): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `lang` | `string`[] |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.acceptsLanguages`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:492

#### acceptsLanguages(lang)

```ts
acceptsLanguages(...lang: string[]): string | false
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| ...`lang` | `string`[] |

##### Returns

`string` \| `false`

##### Inherited from

`express.Request.acceptsLanguages`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:493

***

### addListener()

#### addListener(event, listener)

```ts
addListener(event: "close", listener: () => void): this
```

Event emitter
The defined events on documents including:
1. close
2. data
3. end
4. error
5. pause
6. readable
7. resume

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"close"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.addListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:590

#### addListener(event, listener)

```ts
addListener(event: "data", listener: (chunk: any) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"data"` |
| `listener` | (`chunk`: `any`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.addListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:591

#### addListener(event, listener)

```ts
addListener(event: "end", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"end"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.addListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:592

#### addListener(event, listener)

```ts
addListener(event: "error", listener: (err: Error) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"error"` |
| `listener` | (`err`: `Error`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.addListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:593

#### addListener(event, listener)

```ts
addListener(event: "pause", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"pause"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.addListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:594

#### addListener(event, listener)

```ts
addListener(event: "readable", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"readable"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.addListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:595

#### addListener(event, listener)

```ts
addListener(event: "resume", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"resume"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.addListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:596

#### addListener(event, listener)

```ts
addListener(event: string | symbol, listener: (...args: any[]) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `string` \| `symbol` |
| `listener` | (...`args`: `any`[]) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.addListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:597

***

### asIndexedPairs()

```ts
asIndexedPairs(options?: Pick<ArrayOptions, "signal">): Readable
```

This method returns a new stream with chunks of the underlying stream paired with a counter
in the form `[index, chunk]`. The first index value is `0` and it increases by 1 for each chunk produced.

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `options`? | `Pick`\<`ArrayOptions`, `"signal"`\> |

#### Returns

`Readable`

a stream of indexed pairs.

#### Inherited from

`express.Request.asIndexedPairs`

#### Since

v17.5.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:541

***

### compose()

```ts
compose<T>(stream: ComposeFnParam | T | Iterable<T> | AsyncIterable<T>, options?: {
  "signal": AbortSignal;
 }): T
```

#### Type parameters

| Type parameter |
| :------ |
| `T` *extends* `ReadableStream`\<`T`\> |

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `stream` | `ComposeFnParam` \| `T` \| `Iterable`\<`T`\> \| `AsyncIterable`\<`T`\> |
| `options`? | `object` |
| `options.signal`? | `AbortSignal` |

#### Returns

`T`

#### Inherited from

`express.Request.compose`

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:35

***

### destroy()

```ts
destroy(error?: Error): this
```

Calls `destroy()` on the socket that received the `IncomingMessage`. If `error`is provided, an `'error'` event is emitted on the socket and `error` is passed
as an argument to any listeners on the event.

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `error`? | `Error` |

#### Returns

`this`

#### Inherited from

`express.Request.destroy`

#### Since

v0.3.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/http.d.ts:1355

***

### drop()

```ts
drop(limit: number, options?: Pick<ArrayOptions, "signal">): Readable
```

This method returns a new stream with the first *limit* chunks dropped from the start.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `limit` | `number` | the number of chunks to drop from the readable. |
| `options`? | `Pick`\<`ArrayOptions`, `"signal"`\> | - |

#### Returns

`Readable`

a stream with *limit* chunks dropped from the start.

#### Inherited from

`express.Request.drop`

#### Since

v17.5.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:527

***

### emit()

#### emit(event)

```ts
emit(event: "close"): boolean
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"close"` |

##### Returns

`boolean`

##### Inherited from

`express.Request.emit`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:598

#### emit(event, chunk)

```ts
emit(event: "data", chunk: any): boolean
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"data"` |
| `chunk` | `any` |

##### Returns

`boolean`

##### Inherited from

`express.Request.emit`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:599

#### emit(event)

```ts
emit(event: "end"): boolean
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"end"` |

##### Returns

`boolean`

##### Inherited from

`express.Request.emit`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:600

#### emit(event, err)

```ts
emit(event: "error", err: Error): boolean
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"error"` |
| `err` | `Error` |

##### Returns

`boolean`

##### Inherited from

`express.Request.emit`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:601

#### emit(event)

```ts
emit(event: "pause"): boolean
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"pause"` |

##### Returns

`boolean`

##### Inherited from

`express.Request.emit`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:602

#### emit(event)

```ts
emit(event: "readable"): boolean
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"readable"` |

##### Returns

`boolean`

##### Inherited from

`express.Request.emit`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:603

#### emit(event)

```ts
emit(event: "resume"): boolean
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"resume"` |

##### Returns

`boolean`

##### Inherited from

`express.Request.emit`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:604

#### emit(event, args)

```ts
emit(event: string | symbol, ...args: any[]): boolean
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `string` \| `symbol` |
| ...`args` | `any`[] |

##### Returns

`boolean`

##### Inherited from

`express.Request.emit`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:605

***

### eventNames()

```ts
eventNames(): (string | symbol)[]
```

Returns an array listing the events for which the emitter has registered
listeners. The values in the array are strings or `Symbol`s.

```js
import { EventEmitter } from 'node:events';

const myEE = new EventEmitter();
myEE.on('foo', () => {});
myEE.on('bar', () => {});

const sym = Symbol('symbol');
myEE.on(sym, () => {});

console.log(myEE.eventNames());
// Prints: [ 'foo', 'bar', Symbol(symbol) ]
```

#### Returns

(`string` \| `symbol`)[]

#### Inherited from

`express.Request.eventNames`

#### Since

v6.0.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/events.d.ts:887

***

### every()

```ts
every(fn: (data: any, options?: Pick<ArrayOptions, "signal">) => boolean | Promise<boolean>, options?: ArrayOptions): Promise<boolean>
```

This method is similar to `Array.prototype.every` and calls *fn* on each chunk in the stream
to check if all awaited return values are truthy value for *fn*. Once an *fn* call on a chunk
`await`ed return value is falsy, the stream is destroyed and the promise is fulfilled with `false`.
If all of the *fn* calls on the chunks return a truthy value, the promise is fulfilled with `true`.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `fn` | (`data`: `any`, `options`?: `Pick`\<`ArrayOptions`, `"signal"`\>) => `boolean` \| `Promise`\<`boolean`\> | a function to call on each chunk of the stream. Async or not. |
| `options`? | `ArrayOptions` | - |

#### Returns

`Promise`\<`boolean`\>

a promise evaluating to `true` if *fn* returned a truthy value for every one of the chunks.

#### Inherited from

`express.Request.every`

#### Since

v17.5.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:506

***

### filter()

```ts
filter(fn: (data: any, options?: Pick<ArrayOptions, "signal">) => boolean | Promise<boolean>, options?: ArrayOptions): Readable
```

This method allows filtering the stream. For each chunk in the stream the *fn* function will be called
and if it returns a truthy value, the chunk will be passed to the result stream.
If the *fn* function returns a promise - that promise will be `await`ed.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `fn` | (`data`: `any`, `options`?: `Pick`\<`ArrayOptions`, `"signal"`\>) => `boolean` \| `Promise`\<`boolean`\> | a function to filter chunks from the stream. Async or not. |
| `options`? | `ArrayOptions` | - |

#### Returns

`Readable`

a stream filtered with the predicate *fn*.

#### Inherited from

`express.Request.filter`

#### Since

v17.4.0, v16.14.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:434

***

### find()

#### find(fn, options)

```ts
find<T>(fn: (data: any, options?: Pick<ArrayOptions, "signal">) => data is T, options?: ArrayOptions): Promise<undefined | T>
```

This method is similar to `Array.prototype.find` and calls *fn* on each chunk in the stream
to find a chunk with a truthy value for *fn*. Once an *fn* call's awaited return value is truthy,
the stream is destroyed and the promise is fulfilled with value for which *fn* returned a truthy value.
If all of the *fn* calls on the chunks return a falsy value, the promise is fulfilled with `undefined`.

##### Type parameters

| Type parameter |
| :------ |
| `T` |

##### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `fn` | (`data`: `any`, `options`?: `Pick`\<`ArrayOptions`, `"signal"`\>) => `data is T` | a function to call on each chunk of the stream. Async or not. |
| `options`? | `ArrayOptions` | - |

##### Returns

`Promise`\<`undefined` \| `T`\>

a promise evaluating to the first chunk for which *fn* evaluated with a truthy value,
or `undefined` if no element was found.

##### Inherited from

`express.Request.find`

##### Since

v17.5.0

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:489

#### find(fn, options)

```ts
find(fn: (data: any, options?: Pick<ArrayOptions, "signal">) => boolean | Promise<boolean>, options?: ArrayOptions): Promise<any>
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `fn` | (`data`: `any`, `options`?: `Pick`\<`ArrayOptions`, `"signal"`\>) => `boolean` \| `Promise`\<`boolean`\> |
| `options`? | `ArrayOptions` |

##### Returns

`Promise`\<`any`\>

##### Inherited from

`express.Request.find`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:493

***

### flatMap()

```ts
flatMap(fn: (data: any, options?: Pick<ArrayOptions, "signal">) => any, options?: ArrayOptions): Readable
```

This method returns a new stream by applying the given callback to each chunk of the stream
and then flattening the result.

It is possible to return a stream or another iterable or async iterable from *fn* and the result streams
will be merged (flattened) into the returned stream.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `fn` | (`data`: `any`, `options`?: `Pick`\<`ArrayOptions`, `"signal"`\>) => `any` | a function to map over every chunk in the stream. May be async. May be a stream or generator. |
| `options`? | `ArrayOptions` | - |

#### Returns

`Readable`

a stream flat-mapped with the function *fn*.

#### Inherited from

`express.Request.flatMap`

#### Since

v17.5.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:520

***

### forEach()

```ts
forEach(fn: (data: any, options?: Pick<ArrayOptions, "signal">) => void | Promise<void>, options?: ArrayOptions): Promise<void>
```

This method allows iterating a stream. For each chunk in the stream the *fn* function will be called.
If the *fn* function returns a promise - that promise will be `await`ed.

This method is different from `for await...of` loops in that it can optionally process chunks concurrently.
In addition, a `forEach` iteration can only be stopped by having passed a `signal` option
and aborting the related AbortController while `for await...of` can be stopped with `break` or `return`.
In either case the stream will be destroyed.

This method is different from listening to the `'data'` event in that it uses the `readable` event
in the underlying machinary and can limit the number of concurrent *fn* calls.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `fn` | (`data`: `any`, `options`?: `Pick`\<`ArrayOptions`, `"signal"`\>) => `void` \| `Promise`\<`void`\> | a function to call on each chunk of the stream. Async or not. |
| `options`? | `ArrayOptions` | - |

#### Returns

`Promise`\<`void`\>

a promise for when the stream has finished.

#### Inherited from

`express.Request.forEach`

#### Since

v17.5.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:453

***

### get()

#### get(name)

```ts
get(name: "set-cookie"): undefined | string[]
```

Return request header.

The `Referrer` header field is special-cased,
both `Referrer` and `Referer` are interchangeable.

Examples:

    req.get('Content-Type');
    // => "text/plain"

    req.get('content-type');
    // => "text/plain"

    req.get('Something');
    // => undefined

Aliased as `req.header()`.

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `name` | `"set-cookie"` |

##### Returns

`undefined` \| `string`[]

##### Inherited from

`express.Request.get`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:411

#### get(name)

```ts
get(name: string): undefined | string
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `name` | `string` |

##### Returns

`undefined` \| `string`

##### Inherited from

`express.Request.get`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:412

***

### getMaxListeners()

```ts
getMaxListeners(): number
```

Returns the current max listener value for the `EventEmitter` which is either
set by `emitter.setMaxListeners(n)` or defaults to defaultMaxListeners.

#### Returns

`number`

#### Inherited from

`express.Request.getMaxListeners`

#### Since

v1.0.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/events.d.ts:739

***

### header()

#### header(name)

```ts
header(name: "set-cookie"): undefined | string[]
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `name` | `"set-cookie"` |

##### Returns

`undefined` \| `string`[]

##### Inherited from

`express.Request.header`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:414

#### header(name)

```ts
header(name: string): undefined | string
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `name` | `string` |

##### Returns

`undefined` \| `string`

##### Inherited from

`express.Request.header`

##### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:415

***

### is()

```ts
is(type: string | string[]): null | string | false
```

Check if the incoming request contains the "Content-Type"
header field, and it contains the give mime `type`.

Examples:

     // With Content-Type: text/html; charset=utf-8
     req.is('html');
     req.is('text/html');
     req.is('text/*');
     // => true

     // When Content-Type is application/json
     req.is('json');
     req.is('application/json');
     req.is('application/*');
     // => true

     req.is('html');
     // => false

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `type` | `string` \| `string`[] |

#### Returns

`null` \| `string` \| `false`

#### Inherited from

`express.Request.is`

#### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:551

***

### isPaused()

```ts
isPaused(): boolean
```

The `readable.isPaused()` method returns the current operating state of the`Readable`. This is used primarily by the mechanism that underlies the`readable.pipe()` method. In most
typical cases, there will be no reason to
use this method directly.

```js
const readable = new stream.Readable();

readable.isPaused(); // === false
readable.pause();
readable.isPaused(); // === true
readable.resume();
readable.isPaused(); // === false
```

#### Returns

`boolean`

#### Inherited from

`express.Request.isPaused`

#### Since

v0.11.14

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:287

***

### iterator()

```ts
iterator(options?: {
  "destroyOnReturn": boolean;
}): AsyncIterableIterator<any>
```

The iterator created by this method gives users the option to cancel the destruction
of the stream if the `for await...of` loop is exited by `return`, `break`, or `throw`,
or if the iterator should destroy the stream if the stream emitted an error during iteration.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `options`? | `object` | - |
| `options.destroyOnReturn`? | `boolean` | When set to `false`, calling `return` on the async iterator,<br />or exiting a `for await...of` iteration using a `break`, `return`, or `throw` will not destroy the stream.<br />**Default: `true`**. |

#### Returns

`AsyncIterableIterator`\<`any`\>

#### Inherited from

`express.Request.iterator`

#### Since

v16.3.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:417

***

### listenerCount()

```ts
listenerCount<K>(eventName: string | symbol, listener?: Function): number
```

Returns the number of listeners listening for the event named `eventName`.
If `listener` is provided, it will return how many times the listener is found
in the list of the listeners of the event.

#### Type parameters

| Type parameter |
| :------ |
| `K` |

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `eventName` | `string` \| `symbol` | The name of the event being listened for |
| `listener`? | `Function` | The event handler function |

#### Returns

`number`

#### Inherited from

`express.Request.listenerCount`

#### Since

v3.2.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/events.d.ts:833

***

### listeners()

```ts
listeners<K>(eventName: string | symbol): Function[]
```

Returns a copy of the array of listeners for the event named `eventName`.

```js
server.on('connection', (stream) => {
  console.log('someone connected!');
});
console.log(util.inspect(server.listeners('connection')));
// Prints: [ [Function] ]
```

#### Type parameters

| Type parameter |
| :------ |
| `K` |

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `eventName` | `string` \| `symbol` |

#### Returns

`Function`[]

#### Inherited from

`express.Request.listeners`

#### Since

v0.1.26

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/events.d.ts:752

***

### map()

```ts
map(fn: (data: any, options?: Pick<ArrayOptions, "signal">) => any, options?: ArrayOptions): Readable
```

This method allows mapping over the stream. The *fn* function will be called for every chunk in the stream.
If the *fn* function returns a promise - that promise will be `await`ed before being passed to the result stream.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `fn` | (`data`: `any`, `options`?: `Pick`\<`ArrayOptions`, `"signal"`\>) => `any` | a function to map over every chunk in the stream. Async or not. |
| `options`? | `ArrayOptions` | - |

#### Returns

`Readable`

a stream mapped with the function *fn*.

#### Inherited from

`express.Request.map`

#### Since

v17.4.0, v16.14.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:425

***

### off()

```ts
off<K>(eventName: string | symbol, listener: (...args: any[]) => void): this
```

Alias for `emitter.removeListener()`.

#### Type parameters

| Type parameter |
| :------ |
| `K` |

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `eventName` | `string` \| `symbol` |
| `listener` | (...`args`: `any`[]) => `void` |

#### Returns

`this`

#### Inherited from

`express.Request.off`

#### Since

v10.0.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/events.d.ts:712

***

### on()

#### on(event, listener)

```ts
on(event: "close", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"close"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.on`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:606

#### on(event, listener)

```ts
on(event: "data", listener: (chunk: any) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"data"` |
| `listener` | (`chunk`: `any`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.on`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:607

#### on(event, listener)

```ts
on(event: "end", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"end"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.on`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:608

#### on(event, listener)

```ts
on(event: "error", listener: (err: Error) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"error"` |
| `listener` | (`err`: `Error`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.on`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:609

#### on(event, listener)

```ts
on(event: "pause", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"pause"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.on`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:610

#### on(event, listener)

```ts
on(event: "readable", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"readable"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.on`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:611

#### on(event, listener)

```ts
on(event: "resume", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"resume"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.on`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:612

#### on(event, listener)

```ts
on(event: string | symbol, listener: (...args: any[]) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `string` \| `symbol` |
| `listener` | (...`args`: `any`[]) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.on`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:613

***

### once()

#### once(event, listener)

```ts
once(event: "close", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"close"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.once`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:614

#### once(event, listener)

```ts
once(event: "data", listener: (chunk: any) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"data"` |
| `listener` | (`chunk`: `any`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.once`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:615

#### once(event, listener)

```ts
once(event: "end", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"end"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.once`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:616

#### once(event, listener)

```ts
once(event: "error", listener: (err: Error) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"error"` |
| `listener` | (`err`: `Error`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.once`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:617

#### once(event, listener)

```ts
once(event: "pause", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"pause"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.once`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:618

#### once(event, listener)

```ts
once(event: "readable", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"readable"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.once`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:619

#### once(event, listener)

```ts
once(event: "resume", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"resume"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.once`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:620

#### once(event, listener)

```ts
once(event: string | symbol, listener: (...args: any[]) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `string` \| `symbol` |
| `listener` | (...`args`: `any`[]) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.once`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:621

***

### ~~param()~~

```ts
param(name: string, defaultValue?: any): string
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `name` | `string` |
| `defaultValue`? | `any` |

#### Returns

`string`

#### Inherited from

`express.Request.param`

#### Deprecated

since 4.11 Use either req.params, req.body or req.query, as applicable.

Return the value of param `name` when present or `defaultValue`.

 - Checks route placeholders, ex: _/user/:id_
 - Checks body params, ex: id=12, {"id":12}
 - Checks query string params, ex: ?id=12

To utilize request bodies, `req.body`
should be an object. This can be done by using
the `connect.bodyParser()` middleware.

#### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:528

***

### pause()

```ts
pause(): this
```

The `readable.pause()` method will cause a stream in flowing mode to stop
emitting `'data'` events, switching out of flowing mode. Any data that
becomes available will remain in the internal buffer.

```js
const readable = getReadableStreamSomehow();
readable.on('data', (chunk) => {
  console.log(`Received ${chunk.length} bytes of data.`);
  readable.pause();
  console.log('There will be no additional data for 1 second.');
  setTimeout(() => {
    console.log('Now data will start flowing again.');
    readable.resume();
  }, 1000);
});
```

The `readable.pause()` method has no effect if there is a `'readable'`event listener.

#### Returns

`this`

#### Inherited from

`express.Request.pause`

#### Since

v0.9.4

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:251

***

### pipe()

```ts
pipe<T>(destination: T, options?: {
  "end": boolean;
 }): T
```

#### Type parameters

| Type parameter |
| :------ |
| `T` *extends* `WritableStream`\<`T`\> |

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `destination` | `T` |
| `options`? | `object` |
| `options.end`? | `boolean` |

#### Returns

`T`

#### Inherited from

`express.Request.pipe`

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:29

***

### prependListener()

#### prependListener(event, listener)

```ts
prependListener(event: "close", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"close"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:622

#### prependListener(event, listener)

```ts
prependListener(event: "data", listener: (chunk: any) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"data"` |
| `listener` | (`chunk`: `any`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:623

#### prependListener(event, listener)

```ts
prependListener(event: "end", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"end"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:624

#### prependListener(event, listener)

```ts
prependListener(event: "error", listener: (err: Error) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"error"` |
| `listener` | (`err`: `Error`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:625

#### prependListener(event, listener)

```ts
prependListener(event: "pause", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"pause"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:626

#### prependListener(event, listener)

```ts
prependListener(event: "readable", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"readable"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:627

#### prependListener(event, listener)

```ts
prependListener(event: "resume", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"resume"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:628

#### prependListener(event, listener)

```ts
prependListener(event: string | symbol, listener: (...args: any[]) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `string` \| `symbol` |
| `listener` | (...`args`: `any`[]) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:629

***

### prependOnceListener()

#### prependOnceListener(event, listener)

```ts
prependOnceListener(event: "close", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"close"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependOnceListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:630

#### prependOnceListener(event, listener)

```ts
prependOnceListener(event: "data", listener: (chunk: any) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"data"` |
| `listener` | (`chunk`: `any`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependOnceListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:631

#### prependOnceListener(event, listener)

```ts
prependOnceListener(event: "end", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"end"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependOnceListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:632

#### prependOnceListener(event, listener)

```ts
prependOnceListener(event: "error", listener: (err: Error) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"error"` |
| `listener` | (`err`: `Error`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependOnceListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:633

#### prependOnceListener(event, listener)

```ts
prependOnceListener(event: "pause", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"pause"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependOnceListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:634

#### prependOnceListener(event, listener)

```ts
prependOnceListener(event: "readable", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"readable"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependOnceListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:635

#### prependOnceListener(event, listener)

```ts
prependOnceListener(event: "resume", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"resume"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependOnceListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:636

#### prependOnceListener(event, listener)

```ts
prependOnceListener(event: string | symbol, listener: (...args: any[]) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `string` \| `symbol` |
| `listener` | (...`args`: `any`[]) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.prependOnceListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:637

***

### push()

```ts
push(chunk: any, encoding?: BufferEncoding): boolean
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `chunk` | `any` |
| `encoding`? | `BufferEncoding` |

#### Returns

`boolean`

#### Inherited from

`express.Request.push`

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:407

***

### range()

```ts
range(size: number, options?: Options): undefined | Ranges | Result
```

Parse Range header field, capping to the given `size`.

Unspecified ranges such as "0-" require knowledge of your resource length. In
the case of a byte range this is of course the total number of bytes.
If the Range header field is not given `undefined` is returned.
If the Range header field is given, return value is a result of range-parser.
See more ./types/range-parser/index.d.ts

NOTE: remember that ranges are inclusive, so for example "Range: users=0-3"
should respond with 4 users when available, not 3.

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `size` | `number` |
| `options`? | `Options` |

#### Returns

`undefined` \| `Ranges` \| `Result`

#### Inherited from

`express.Request.range`

#### Source

node\_modules/.pnpm/@types+express-serve-static-core@4.17.43/node\_modules/@types/express-serve-static-core/index.d.ts:507

***

### rawListeners()

```ts
rawListeners<K>(eventName: string | symbol): Function[]
```

Returns a copy of the array of listeners for the event named `eventName`,
including any wrappers (such as those created by `.once()`).

```js
import { EventEmitter } from 'node:events';
const emitter = new EventEmitter();
emitter.once('log', () => console.log('log once'));

// Returns a new Array with a function `onceWrapper` which has a property
// `listener` which contains the original listener bound above
const listeners = emitter.rawListeners('log');
const logFnWrapper = listeners[0];

// Logs "log once" to the console and does not unbind the `once` event
logFnWrapper.listener();

// Logs "log once" to the console and removes the listener
logFnWrapper();

emitter.on('log', () => console.log('log persistently'));
// Will return a new Array with a single function bound by `.on()` above
const newListeners = emitter.rawListeners('log');

// Logs "log persistently" twice
newListeners[0]();
emitter.emit('log');
```

#### Type parameters

| Type parameter |
| :------ |
| `K` |

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `eventName` | `string` \| `symbol` |

#### Returns

`Function`[]

#### Inherited from

`express.Request.rawListeners`

#### Since

v9.4.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/events.d.ts:783

***

### read()

```ts
read(size?: number): any
```

The `readable.read()` method reads data out of the internal buffer and
returns it. If no data is available to be read, `null` is returned. By default,
the data is returned as a `Buffer` object unless an encoding has been
specified using the `readable.setEncoding()` method or the stream is operating
in object mode.

The optional `size` argument specifies a specific number of bytes to read. If`size` bytes are not available to be read, `null` will be returned _unless_the stream has ended, in which
case all of the data remaining in the internal
buffer will be returned.

If the `size` argument is not specified, all of the data contained in the
internal buffer will be returned.

The `size` argument must be less than or equal to 1 GiB.

The `readable.read()` method should only be called on `Readable` streams
operating in paused mode. In flowing mode, `readable.read()` is called
automatically until the internal buffer is fully drained.

```js
const readable = getReadableStreamSomehow();

// 'readable' may be triggered multiple times as data is buffered in
readable.on('readable', () => {
  let chunk;
  console.log('Stream is readable (new data received in buffer)');
  // Use a loop to make sure we read all currently available data
  while (null !== (chunk = readable.read())) {
    console.log(`Read ${chunk.length} bytes of data...`);
  }
});

// 'end' will be triggered once when there is no more data available
readable.on('end', () => {
  console.log('Reached end of stream.');
});
```

Each call to `readable.read()` returns a chunk of data, or `null`. The chunks
are not concatenated. A `while` loop is necessary to consume all data
currently in the buffer. When reading a large file `.read()` may return `null`,
having consumed all buffered content so far, but there is still more data to
come not yet buffered. In this case a new `'readable'` event will be emitted
when there is more data in the buffer. Finally the `'end'` event will be
emitted when there is no more data to come.

Therefore to read a file's whole contents from a `readable`, it is necessary
to collect chunks across multiple `'readable'` events:

```js
const chunks = [];

readable.on('readable', () => {
  let chunk;
  while (null !== (chunk = readable.read())) {
    chunks.push(chunk);
  }
});

readable.on('end', () => {
  const content = chunks.join('');
});
```

A `Readable` stream in object mode will always return a single item from
a call to `readable.read(size)`, regardless of the value of the`size` argument.

If the `readable.read()` method returns a chunk of data, a `'data'` event will
also be emitted.

Calling [read](RequestWithAuth.md#read) after the `'end'` event has
been emitted will return `null`. No runtime error will be raised.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `size`? | `number` | Optional argument to specify how much data to read. |

#### Returns

`any`

#### Inherited from

`express.Request.read`

#### Since

v0.9.4

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:204

***

### reduce()

#### reduce(fn, initial, options)

```ts
reduce<T>(
   fn: (previous: any, data: any, options?: Pick<ArrayOptions, "signal">) => T, 
   initial?: undefined, 
options?: Pick<ArrayOptions, "signal">): Promise<T>
```

This method calls *fn* on each chunk of the stream in order, passing it the result from the calculation
on the previous element. It returns a promise for the final value of the reduction.

If no *initial* value is supplied the first chunk of the stream is used as the initial value.
If the stream is empty, the promise is rejected with a `TypeError` with the `ERR_INVALID_ARGS` code property.

The reducer function iterates the stream element-by-element which means that there is no *concurrency* parameter
or parallelism. To perform a reduce concurrently, you can extract the async function to `readable.map` method.

##### Type parameters

| Type parameter | Value |
| :------ | :------ |
| `T` | `any` |

##### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `fn` | (`previous`: `any`, `data`: `any`, `options`?: `Pick`\<`ArrayOptions`, `"signal"`\>) => `T` | a reducer function to call over every chunk in the stream. Async or not. |
| `initial`? | `undefined` | the initial value to use in the reduction. |
| `options`? | `Pick`\<`ArrayOptions`, `"signal"`\> | - |

##### Returns

`Promise`\<`T`\>

a promise for the final value of the reduction.

##### Inherited from

`express.Request.reduce`

##### Since

v17.5.0

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:556

#### reduce(fn, initial, options)

```ts
reduce<T>(
   fn: (previous: T, data: any, options?: Pick<ArrayOptions, "signal">) => T, 
   initial: T, 
options?: Pick<ArrayOptions, "signal">): Promise<T>
```

##### Type parameters

| Type parameter | Value |
| :------ | :------ |
| `T` | `any` |

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `fn` | (`previous`: `T`, `data`: `any`, `options`?: `Pick`\<`ArrayOptions`, `"signal"`\>) => `T` |
| `initial` | `T` |
| `options`? | `Pick`\<`ArrayOptions`, `"signal"`\> |

##### Returns

`Promise`\<`T`\>

##### Inherited from

`express.Request.reduce`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:561

***

### removeAllListeners()

```ts
removeAllListeners(event?: string | symbol): this
```

Removes all listeners, or those of the specified `eventName`.

It is bad practice to remove listeners added elsewhere in the code,
particularly when the `EventEmitter` instance was created by some other
component or module (e.g. sockets or file streams).

Returns a reference to the `EventEmitter`, so that calls can be chained.

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `event`? | `string` \| `symbol` |

#### Returns

`this`

#### Inherited from

`express.Request.removeAllListeners`

#### Since

v0.1.26

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/events.d.ts:723

***

### removeListener()

#### removeListener(event, listener)

```ts
removeListener(event: "close", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"close"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.removeListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:638

#### removeListener(event, listener)

```ts
removeListener(event: "data", listener: (chunk: any) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"data"` |
| `listener` | (`chunk`: `any`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.removeListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:639

#### removeListener(event, listener)

```ts
removeListener(event: "end", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"end"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.removeListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:640

#### removeListener(event, listener)

```ts
removeListener(event: "error", listener: (err: Error) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"error"` |
| `listener` | (`err`: `Error`) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.removeListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:641

#### removeListener(event, listener)

```ts
removeListener(event: "pause", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"pause"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.removeListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:642

#### removeListener(event, listener)

```ts
removeListener(event: "readable", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"readable"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.removeListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:643

#### removeListener(event, listener)

```ts
removeListener(event: "resume", listener: () => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `"resume"` |
| `listener` | () => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.removeListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:644

#### removeListener(event, listener)

```ts
removeListener(event: string | symbol, listener: (...args: any[]) => void): this
```

##### Parameters

| Parameter | Type |
| :------ | :------ |
| `event` | `string` \| `symbol` |
| `listener` | (...`args`: `any`[]) => `void` |

##### Returns

`this`

##### Inherited from

`express.Request.removeListener`

##### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:645

***

### resume()

```ts
resume(): this
```

The `readable.resume()` method causes an explicitly paused `Readable` stream to
resume emitting `'data'` events, switching the stream into flowing mode.

The `readable.resume()` method can be used to fully consume the data from a
stream without actually processing any of that data:

```js
getReadableStreamSomehow()
  .resume()
  .on('end', () => {
    console.log('Reached the end, but did not read anything.');
  });
```

The `readable.resume()` method has no effect if there is a `'readable'`event listener.

#### Returns

`this`

#### Inherited from

`express.Request.resume`

#### Since

v0.9.4

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:270

***

### setEncoding()

```ts
setEncoding(encoding: BufferEncoding): this
```

The `readable.setEncoding()` method sets the character encoding for
data read from the `Readable` stream.

By default, no encoding is assigned and stream data will be returned as`Buffer` objects. Setting an encoding causes the stream data
to be returned as strings of the specified encoding rather than as `Buffer`objects. For instance, calling `readable.setEncoding('utf8')` will cause the
output data to be interpreted as UTF-8 data, and passed as strings. Calling`readable.setEncoding('hex')` will cause the data to be encoded in hexadecimal
string format.

The `Readable` stream will properly handle multi-byte characters delivered
through the stream that would otherwise become improperly decoded if simply
pulled from the stream as `Buffer` objects.

```js
const readable = getReadableStreamSomehow();
readable.setEncoding('utf8');
readable.on('data', (chunk) => {
  assert.equal(typeof chunk, 'string');
  console.log('Got %d characters of string data:', chunk.length);
});
```

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `encoding` | `BufferEncoding` | The encoding to use. |

#### Returns

`this`

#### Inherited from

`express.Request.setEncoding`

#### Since

v0.9.4

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:229

***

### setMaxListeners()

```ts
setMaxListeners(n: number): this
```

By default `EventEmitter`s will print a warning if more than `10` listeners are
added for a particular event. This is a useful default that helps finding
memory leaks. The `emitter.setMaxListeners()` method allows the limit to be
modified for this specific `EventEmitter` instance. The value can be set to`Infinity` (or `0`) to indicate an unlimited number of listeners.

Returns a reference to the `EventEmitter`, so that calls can be chained.

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `n` | `number` |

#### Returns

`this`

#### Inherited from

`express.Request.setMaxListeners`

#### Since

v0.3.5

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/events.d.ts:733

***

### setTimeout()

```ts
setTimeout(msecs: number, callback?: () => void): this
```

Calls `message.socket.setTimeout(msecs, callback)`.

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `msecs` | `number` |
| `callback`? | () => `void` |

#### Returns

`this`

#### Inherited from

`express.Request.setTimeout`

#### Since

v0.5.9

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/http.d.ts:1288

***

### some()

```ts
some(fn: (data: any, options?: Pick<ArrayOptions, "signal">) => boolean | Promise<boolean>, options?: ArrayOptions): Promise<boolean>
```

This method is similar to `Array.prototype.some` and calls *fn* on each chunk in the stream
until the awaited return value is `true` (or any truthy value). Once an *fn* call on a chunk
`await`ed return value is truthy, the stream is destroyed and the promise is fulfilled with `true`.
If none of the *fn* calls on the chunks return a truthy value, the promise is fulfilled with `false`.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `fn` | (`data`: `any`, `options`?: `Pick`\<`ArrayOptions`, `"signal"`\>) => `boolean` \| `Promise`\<`boolean`\> | a function to call on each chunk of the stream. Async or not. |
| `options`? | `ArrayOptions` | - |

#### Returns

`Promise`\<`boolean`\>

a promise evaluating to `true` if *fn* returned a truthy value for at least one of the chunks.

#### Inherited from

`express.Request.some`

#### Since

v17.5.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:475

***

### take()

```ts
take(limit: number, options?: Pick<ArrayOptions, "signal">): Readable
```

This method returns a new stream with the first *limit* chunks.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `limit` | `number` | the number of chunks to take from the readable. |
| `options`? | `Pick`\<`ArrayOptions`, `"signal"`\> | - |

#### Returns

`Readable`

a stream with *limit* chunks taken.

#### Inherited from

`express.Request.take`

#### Since

v17.5.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:534

***

### toArray()

```ts
toArray(options?: Pick<ArrayOptions, "signal">): Promise<any[]>
```

This method allows easily obtaining the contents of a stream.

As this method reads the entire stream into memory, it negates the benefits of streams. It's intended
for interoperability and convenience, not as the primary way to consume streams.

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `options`? | `Pick`\<`ArrayOptions`, `"signal"`\> |

#### Returns

`Promise`\<`any`[]\>

a promise containing an array with the contents of the stream.

#### Inherited from

`express.Request.toArray`

#### Since

v17.5.0

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:465

***

### unpipe()

```ts
unpipe(destination?: WritableStream): this
```

The `readable.unpipe()` method detaches a `Writable` stream previously attached
using the [pipe](RequestWithAuth.md#pipe) method.

If the `destination` is not specified, then _all_ pipes are detached.

If the `destination` is specified, but no pipe is set up for it, then
the method does nothing.

```js
const fs = require('node:fs');
const readable = getReadableStreamSomehow();
const writable = fs.createWriteStream('file.txt');
// All the data from readable goes into 'file.txt',
// but only for the first second.
readable.pipe(writable);
setTimeout(() => {
  console.log('Stop writing to file.txt.');
  readable.unpipe(writable);
  console.log('Manually close the file stream.');
  writable.end();
}, 1000);
```

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `destination`? | `WritableStream` | Optional specific stream to unpipe |

#### Returns

`this`

#### Inherited from

`express.Request.unpipe`

#### Since

v0.9.4

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:314

***

### unshift()

```ts
unshift(chunk: any, encoding?: BufferEncoding): void
```

Passing `chunk` as `null` signals the end of the stream (EOF) and behaves the
same as `readable.push(null)`, after which no more data can be written. The EOF
signal is put at the end of the buffer and any buffered data will still be
flushed.

The `readable.unshift()` method pushes a chunk of data back into the internal
buffer. This is useful in certain situations where a stream is being consumed by
code that needs to "un-consume" some amount of data that it has optimistically
pulled out of the source, so that the data can be passed on to some other party.

The `stream.unshift(chunk)` method cannot be called after the `'end'` event
has been emitted or a runtime error will be thrown.

Developers using `stream.unshift()` often should consider switching to
use of a `Transform` stream instead. See the `API for stream implementers` section for more information.

```js
// Pull off a header delimited by \n\n.
// Use unshift() if we get too much.
// Call the callback with (error, header, stream).
const { StringDecoder } = require('node:string_decoder');
function parseHeader(stream, callback) {
  stream.on('error', callback);
  stream.on('readable', onReadable);
  const decoder = new StringDecoder('utf8');
  let header = '';
  function onReadable() {
    let chunk;
    while (null !== (chunk = stream.read())) {
      const str = decoder.write(chunk);
      if (str.includes('\n\n')) {
        // Found the header boundary.
        const split = str.split(/\n\n/);
        header += split.shift();
        const remaining = split.join('\n\n');
        const buf = Buffer.from(remaining, 'utf8');
        stream.removeListener('error', callback);
        // Remove the 'readable' listener before unshifting.
        stream.removeListener('readable', onReadable);
        if (buf.length)
          stream.unshift(buf);
        // Now the body of the message can be read from the stream.
        callback(null, header, stream);
        return;
      }
      // Still reading the header.
      header += str;
    }
  }
}
```

Unlike [push](RequestWithAuth.md#push), `stream.unshift(chunk)` will not
end the reading process by resetting the internal reading state of the stream.
This can cause unexpected results if `readable.unshift()` is called during a
read (i.e. from within a [_read](RequestWithAuth.md#_read) implementation on a
custom stream). Following the call to `readable.unshift()` with an immediate [push](RequestWithAuth.md#push) will reset the reading state appropriately,
however it is best to simply avoid calling `readable.unshift()` while in the
process of performing a read.

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `chunk` | `any` | Chunk of data to unshift onto the read queue. For streams not operating in object mode, `chunk` must be a string, `Buffer`, `Uint8Array`, or `null`. For object mode<br />streams, `chunk` may be any JavaScript value. |
| `encoding`? | `BufferEncoding` | Encoding of string chunks. Must be a valid `Buffer` encoding, such as `'utf8'` or `'ascii'`. |

#### Returns

`void`

#### Inherited from

`express.Request.unshift`

#### Since

v0.9.11

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:380

***

### wrap()

```ts
wrap(stream: ReadableStream): this
```

Prior to Node.js 0.10, streams did not implement the entire `node:stream`module API as it is currently defined. (See `Compatibility` for more
information.)

When using an older Node.js library that emits `'data'` events and has a [pause](RequestWithAuth.md#pause) method that is advisory only, the`readable.wrap()` method can be used to create a `Readable`
stream that uses
the old stream as its data source.

It will rarely be necessary to use `readable.wrap()` but the method has been
provided as a convenience for interacting with older Node.js applications and
libraries.

```js
const { OldReader } = require('./old-api-module.js');
const { Readable } = require('node:stream');
const oreader = new OldReader();
const myReader = new Readable().wrap(oreader);

myReader.on('readable', () => {
  myReader.read(); // etc.
});
```

#### Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `stream` | `ReadableStream` | An "old style" readable stream |

#### Returns

`this`

#### Inherited from

`express.Request.wrap`

#### Since

v0.9.4

#### Source

node\_modules/.pnpm/@types+node@20.11.30/node\_modules/@types/node/stream.d.ts:406
