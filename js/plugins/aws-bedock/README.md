<h1 align="center">
  Genkit <> AWS Bedrock Plugin
</h1>

<h4 align="center">AWS Bedrock Plugin for Genkit</h4>


**`@genkit-ai/aws-bedrock`** is a plugin for using AWS Bedrock APIs with
[Genkit](https://github.com/firebase/genkit).

## Installation

Install the plugin in your project with your favourite package manager

- `npm install @genkit-ai/aws-bedrock`
- `pnpm add @genkit-ai/aws-bedrock`

### Versions

if you are using Genkit version `<v0.9.0`, please use the plugin version `v1.9.0`. If you are using Genkit `>=v0.9.0`, please use the plugin version `>=v1.10.0`.

## Usage

### Configuration

To use the plugin, you need to configure it with your AWS credentials. There are several approaches depending on your environment.

#### Standard Initialization

You can configure the plugin by calling the `genkit` function with your AWS region and model:

```typescript
import { genkit, z } from 'genkit';
import { awsBedrock, amazonNovaProV1 } from "@genkit-ai/aws-bedrock";

const ai = genkit({
  plugins: [
    awsBedrock({ region: "<my-region>" }),
  ],
   model: amazonNovaProV1,
});
```

If you have set the `AWS_` environment variables, you can initialize it like this:

```typescript
import { genkit, z } from 'genkit';
import { awsBedrock, amazonNovaProV1 } from "@genkit-ai/aws-bedrock";

const ai = genkit({
  plugins: [
    awsBedrock(),
  ],
   model: amazonNovaProV1,
});
```

#### Production Environment Authentication

In production environments, it is often necessary to install an additional library to handle authentication. One approach is to use the `@aws-sdk/credential-providers` package:

```typescript
import { fromEnv } from "@aws-sdk/credential-providers";
const ai = genkit({
  plugins: [
    awsBedrock({
      region: "us-east-1",
      credentials: fromEnv(),
    }),
  ],
});
```

Ensure you have a `.env` file with the necessary AWS credentials. Remember that the .env file must be added to your .gitignore to prevent sensitive credentials from being exposed.

```
AWS_ACCESS_KEY_ID = 
AWS_SECRET_ACCESS_KEY =
```

#### Local Environment Authentication

For local development, you can directly supply the credentials:

```typescript
const ai = genkit({
  plugins: [
    awsBedrock({
      region: "us-east-1",
      credentials: {
        accessKeyId: awsAccessKeyId.value(),
        secretAccessKey: awsSecretAccessKey.value(),
      },
    }),
  ],
});
```

Each approach allows you to manage authentication effectively based on your environment needs. 


### Configuration with Inference Endpoint

If you want to use a model that uses [Cross-region Inference Endpoints](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html), you can specify the region in the model configuration. Cross-region inference uses inference profiles to increase throughput and improve resiliency by routing your requests across multiple AWS Regions during peak utilization bursts:


```typescript
import { genkit, z } from 'genkit';
import {awsBedrock, amazonNovaProV1, anthropicClaude35SonnetV2} from "@genkit-ai/aws-bedrock";

const ai = genkit({
  plugins: [
    awsBedrock(),
  ],
   model: anthropicClaude35SonnetV2("us"),
});
```


### Basic examples

The simplest way to call the text generation model is by using the helper function `generate`:

```typescript
import { genkit, z } from 'genkit';
import {awsBedrock, amazonNovaProV1} from "@genkit-ai/aws-bedrock";

// Basic usage of an LLM
const response = await ai.generate({
  prompt: 'Tell me a joke.',
});

console.log(await response.text);
```

### Within a flow

```typescript
// ...configure Genkit (as shown above)...

export const myFlow = ai.defineFlow(
  {
    name: 'menuSuggestionFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    const llmResponse = await ai.generate({
      prompt: `Suggest an item for the menu of a ${subject} themed restaurant`,
    });

    return llmResponse.text;
  }
);
```

### Tool use

```typescript
// ...configure Genkit (as shown above)...

const specialToolInputSchema = z.object({ meal: z.enum(["breakfast", "lunch", "dinner"]) });
const specialTool = ai.defineTool(
  {
    name: "specialTool",
    description: "Retrieves today's special for the given meal",
    inputSchema: specialToolInputSchema,
    outputSchema: z.string(),
  },
  async ({ meal }): Promise<string> => {
    // Retrieve up-to-date information and return it. Here, we just return a
    // fixed value.
    return "Baked beans on toast";
  }
);

const result = ai.generate({
  tools: [specialTool],
  prompt: "What's for breakfast?",
});

console.log(result.then((res) => res.text));
```

For more detailed examples and the explanation of other functionalities, refer to the [official Genkit documentation](https://firebase.google.com/docs/genkit/get-started).

## Using Custom Models

If you want to use a model that is not exported by this plugin, you can register it using the `customModels` option when initializing the plugin:

```typescript
import { genkit, z } from 'genkit';
import { awsBedrock } from '@genkit-ai/aws-bedrock';

const ai = genkit({
  plugins: [
    awsBedrock({
      region: 'us-east-1',
      customModels: ['openai.gpt-oss-20b-1:0'], // Register custom models
    }),
  ],
});

// Use the custom model by specifying its name as a string
export const customModelFlow = ai.defineFlow(
  {
    name: 'customModelFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    const llmResponse = await ai.generate({
      model: 'aws-bedrock/openai.gpt-oss-20b-1:0', // Use any registered custom model
      prompt: `Tell me about ${subject}`,
    });
    return llmResponse.text;
  }
);
```

Alternatively, you can define a custom model outside of the plugin initialization:

```typescript
import { defineAwsBedrockModel } from '@genkit-ai/aws-bedrock';

const customModel = defineAwsBedrockModel('openai.gpt-oss-20b-1:0', {
  region: 'us-east-1'
});

const response = await ai.generate({
  model: customModel,
  prompt: 'Hello!'
});
```

## Supported models

This plugin supports all currently available **Chat/Completion** and **Embeddings** models from AWS Bedrock. This plugin supports image input and multimodal models.


## Need support?

> [!NOTE]  
> This repository depends on Google's Firebase Genkit. For issues and questions related to Genkit, please refer to instructions available in [Genkit's repository](https://github.com/firebase/genkit).

Reach out by opening a discussion on [GitHub Discussions](https://github.com/firebase/genkit/genkit).


## License

This project is licensed under the [Apache 2.0 License](https://github.com/firebase/genkit/blob/main/LICENSE).

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202%2E0-lightgrey.svg)](https://github.com/firebase/genkit/blob/main/LICENSE)