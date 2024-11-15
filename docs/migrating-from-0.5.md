# Migrating from 0.5

Genkit 0.9 introduces a number of breaking changes alongside feature enhancements that improve overall functionality. If you have been developing applications with Genkit 0.5, you will need to update your application code when you upgrade to the latest version. This guide outlines the most significant changes and offers steps to migrate your existing applications smoothly.

## Quickstart guide

The following steps will help you migrate from Genkit 0.5 to Genkit 0.9 quickly. Read more information about these changes in the detailed [Changelog](#changelog) below.

### 1. Install the new CLI

* Uninstall the old CLI

  ```posix-terminal
  npm uninstall -g genkit && npm uninstall genkit
  ```

* Install the new CLI

  ```posix-terminal
  npm i -D genkit-cli
  ```

### 2. Update your dependencies

* Remove individual Genkit core packages

  ```posix-terminal
  npm uninstall @genkit-ai/ai @genkit-ai/core @genkit-ai/dotprompt @genkit-ai/flow
  ```

* Install the new consolidated `genkit` package

  ```posix-terminal
  npm i --save genkit
  ```

* Upgrade all plugin versions (example below)

  ```
  npm upgrade @genkit-ai/firebase
  ```

### 3. Change your imports

* Remove imports for individual Genkit core packages

  ```js
  import { … } from '@genkit-ai/ai';
  import { … } from '@genkit-ai/core';
  import { … } from '@genkit-ai/flow';
  ```

* Remove zod imports

  ```js
  import * as z from 'zod';
  ```

* Import `genkit` and `zod` from `genkit`

  ```js
  import { z, genkit } from 'genkit';
  ```

### 4. Update your code

#### Remove the configureGenkit blocks 

Configuration for Genkit is now done per instance. Telemetry and logging is configured globally and separately from the Genkit instance. 

* Replace `configureGenkit` with `ai = genkit({...})` blocks. Keep only the plugin configuration.

  ```js
  import { genkit } from 'genkit';

  const ai = genkit({ plugins: [...]});
  ```

* Configure telemetry using enableFirebaseTelemetry or enableGoogleCloudTelemetry

  For Firebase:

  ```js
  import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

  enableFirebaseTelemetry({...});
  ```

  For Google Cloud:

  ```js
  import { enableGoogleCloudTelemetry } from '@genkit-ai/google-cloud';

  enableGoogleCloudTelemetry({...});
  ```

* Set your logging level independently

  ```js
  import { logger } from 'genkit/logging';

  logger.setLogLevel('debug');
  ```

See the [Monitoring and Logging](./monitoring.md) documentation for more details on how to configure telemetry and logging.

See the [Get Started](./get-started.md) documentation for more details on how to configure a Genkit instance.

#### Migrate Genkit actions to be called from the `genkit` instance

Actions (flows, tools, retrievers, indexers, etc.) are defined per instance. Read the [Changelog](#changelog) for all of the features you will need to change, but here is an example of some common ones.

```js
import { genkit } from 'genkit';
import { onFlow } from '@genkit-ai/firebase/functions';

const ai = genkit({ plugins: [...]});

// Flows and tools are defined on the specific genkit instance
// and are directly callable.
const sampleFlow = ai.defineFlow(...);
const sampleTool = ai.defineTool(...);

async function callMyFlow() {
  // Previously, text output could accessed via .text()
  // Now it is either .output() or .text
  return await sampleFlow().output();
}

// onFlow now takes the Genkit instance as first argument
// This registers the flow as a callable firebase function
onFlow(ai, ...);
const flows = [ sampleFlow, ... ];
// Start the flow server to make the registered flows callable over HTTP
ai.startFlowServer({flows});
```

### 5. Run it

```posix-terminal
# run the DevUI and your js code
genkit start -- <command to run node>

# run a defined flow
genkit flow:run <flowName>
```

## Changelog

### 1. CLI Changes

The command-line interface (CLI) has undergone significant updates in Genkit 0.9. The command to start Genkit has changed, and the CLI has been separated into its own standalone package, which you now need to install separately.

To install the CLI:

```posix-terminal
npm i -g genkit-cli
```

Some changes have been made to the `genkit start` command:

Starts your Genkit application code + Dev UI together:

```posix-terminal
genkit start -- [start command]

genkit start -- tsx src/index.ts

genkit start -- go run main.go
```

Watch mode is supported as well:

```posix-terminal
genkit start -- tsx --watch src/index.ts
```

Starts ONLY your application code in Genkit dev mode:

```posix-terminal
genkit start --noui -- <start command>

genkit start --noui -- tsx src/index.ts
```
Starts the Dev UI ONLY:

```posix-terminal
genkit start
```

Previously, the `genkit start` command would start the Dev UI and your application code together. If you have any CI/CD pipelines relying on this command, you may need to update the pipeline.

The Dev UI will interact directly with the flow server to figure out which flows are registered and allow you to invoke them directly with sample inputs.

### 2. Simplified packages and imports

Previously, the Genkit libraries were separated into several modules, which you needed to install and import individually. These modules have now been consolidated into a single import. In addition, the Zod module is now re-exported by Genkit.

**Old:**

```posix-terminal
npm i @genkit-ai/core @genkit-ai/ai @genkit-ai/flow @genkit-ai/dotprompt
```

**New:**

```posix-terminal
npm i genkit
```

**Old:**

```js
import { … } from '@genkit-ai/ai';
import { … } from '@genkit-ai/core';
import { … } from '@genkit-ai/flow';
import * as z from 'zod';
```

**New:**

```js
import { genkit, z } from 'genkit';
```

Genkit plugins still must be installed and imported individually.

### 3. Configuring Genkit

Previously, initializing Genkit was done once globally by calling the `configureGenkit` function. Genkit resources (flows, tools, prompts, etc.) would all automatically be wired with this global configuration.

Genkit 0.9 introduces `Genkit` instances, each of which encapsulates a configuration. See the following examples:

**Old:**

```js
import { configureGenkit } from '@genkit-ai/core';

configureGenkit({
  telemetry: {
    instrumentation: ...,
    logger: ...
  }
});
```

**New:**

```js
import { genkit } from 'genkit';
import { logger } from 'genkit/logging';
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

logger.setLogLevel('debug');
enableFirebaseTelemetry({...});

const ai = genkit({ ... });
```

Let’s break it down:

- `configureGenkit()` has been replaced with `genkit()`, and it returns a configured `Genkit` instance rather than setting up configurations globally.
- The Genkit initialization function  is now in the `genkit` package.
- Logging and telemetry are still configured globally using their own explicit methods. These configurations apply uniformly across all `Genkit` instances.

### 4. Defining flows and starting the flow server explicitly

Now that you have a configured `Genkit` instance, you will need to define your flows. All core developer-facing API methods like `defineFlow`, `defineTool`, and `onFlow` are now invoked through this instance.

This is distinct from the previous way, where flows and tools were registered globally.

**Old:**

```js
import { defineFlow, defineTool, onFlow } from '@genkit-ai/core';

defineFlow(...);
defineTool(...);

onFlow(...);
```

**New:**

```js
// Define tools and flows
const sampleFlow = ai.defineFlow(...);
const sampleTool = ai.defineTool(...);

// onFlow now takes the Genkit instance as first argument
// This registers the flow as a callable firebase function
onFlow(ai, ...);  

const flows = [ sampleFlow, ... ];
// Start the flow server to make the registered flows callable over HTTP
ai.startFlowServer({flows});
```

As of now, all flows that you want to make available need to be explicitly registered in the `flows` array above.

### 5. Tools and Prompts must be statically defined 

In earlier versions of Genkit, you could dynamically define tools and prompts at runtime, directly from within a flow.

In Genkit 0.9, this behavior is no longer allowed. Instead, you need to define all actions and flows outside of the flow’s execution (i.e. statically).

This change enforces a stricter separation of action definitions from execution.

If any of your code is defined dynamically, they need to be refactored. Otherwise, an error will be thrown at runtime when the flow is executed.

**❌ DON'T:**

```js
const flow = defineFlow({...}, async (input) => {
  const tool = defineTool({...});
  await tool(...);
});
```

**✅ DO:**

```js
const tool = ai.defineTool({...});

const flow = ai.defineFlow({...}, async (input) => {
  await tool(...);
});
```

### 6. New API for Streaming Flows

In Genkit 0.9, we have simplified the syntax for defining a streaming flow and invoking it. 

First, `defineFlow` and `defineStreamingFlow` have been separated. If you have a flow that is meant to be streamed, you will have to update your code to define it via `defineStreamingFlow`.

Second, instead of calling separate `stream()` and `response()` functions, both stream and response are now values returned directly from the flow. This change simplifies flow streaming.

**Old:**

```js
import { defineFlow, streamFlow } from '@genkit-ai/flow';

const myStreamingFlow = defineFlow(...);
const { stream, output } = await streamFlow(myStreamingFlow, ...);

for await (const chunk of stream()) {
  console.log(chunk);
}

console.log(await output());
```

**New:**

```js
const myStreamingFlow = ai.defineStreamingFlow(...);
const { stream, response } = await myStreamingFlow(...);

for await (const chunk of stream) {
  console.log(chunk);
}

console.log(await response);
```

### 7. GenerateResponse class methods replaced with getter properties

Previously, you used to access the structured output or text of the response using class methods, like `output()` or `text()`.

In Genkit 0.9, those methods have been replaced by getter properties. This simplifies working with responses.

**Old:**

```js
const response = await generate({ prompt: 'hi' });
console.log(response.text());
```

**New:**

```js
const response = await ai.generate('hi');
console.log(response.text);
```
The same applies to `output`:

**Old:**

```js
console.log(response.output());
```

**New:**

```js
console.log(response.output);
```

### 8. Candidate Generation Eliminated

Genkit 0.9 simplifies response handling by removing the `candidates` attribute. Previously, responses could contain multiple candidates, which you needed to handle explicitly. Now, only the first candidate is returned directly in a flat response. 

Any code that accesses the candidates directly will not work anymore.

**Old:**

```js
const response = await generate({
 messages: [ { role: 'user', content: ...} ]
});
console.log(response.candidates); // previously you could access candidates directly
```

**New:**

```js
const response = await ai.generate({
 messages: [ { role: 'user', content: ...} ]
});
console.log(response.message); // single candidate is returned directly in a flat response
```

### 9. Generate API - Multi-Turn enhancements

For multi-turn conversations, the old `toHistory()` method has been replaced by `messages`, further simplifying how conversation history is handled.

**Old:**

```js
const history = response.toHistory();
```

**New:**

```js
const response = await ai.generate({
 messages: [ { role: 'user', content: ...} ]
});
const history = response.messages;
```

### 10. Streamlined Chat API

In Genkit 0.9, the Chat API has been redesigned for easier session management and interaction. Here’s how you can leverage it for both synchronous and streaming chat experiences:

```js
import { genkit } from 'genkit';
import { gemini15Flash, googleAI } from '@genkit-ai/googleai';

const ai = genkit({
 plugins: [googleAI()],
 model: gemini15Flash,
});

const session = ai.createSession({ store: firestoreSessionStore() });
const chat = await session.chat({ system: 'talk like a pirate' });

let response = await chat.send('hi, my name is Pavel');
console.log(response.text()); // "hi Pavel, I'm llm"

// continue the conversation
response = await chat.send("what's my name");
console.log(response.text()); // "Pavel"

// can stream
const { response, stream } = await chat.sendStream('bye');
for await (const chunk of stream) {
 console.log(chunk.text());
}
console.log((await response).text());

// can load session from the store
const prevSession = await ai.loadSession(session.id, { store });
const prevChat = await prevSession.chat();
await prevChat.send('bye');
```
