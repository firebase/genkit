# Vertex AI plugin

The Vertex AI plugin provides interfaces to several Google generative AI models
through the [Vertex AI API](https://cloud.google.com/vertex-ai/generative-ai/docs/):

- Gemini 1.0 Pro and Gemini 1.0 Pro Vision text generation
- Imagen2 image generation
- Gecko text embedding generation

It also provides access to subset of evaluation metrics through the Vertex AI [Rapid Evaluation API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation).

- [BLEU](https://cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/projects.locations/evaluateInstances#bleuinput)
- [ROUGE](https://cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/projects.locations/evaluateInstances#rougeinput)
- [Fluency](https://cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/projects.locations/evaluateInstances#fluencyinput)
- [Safety](https://cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/projects.locations/evaluateInstances#safetyinput)
- [Groundeness](https://cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/projects.locations/evaluateInstances#groundednessinput)
- [Summarization Quality](https://cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/projects.locations/evaluateInstances#summarizationqualityinput)
- [Summarization Helpfulness](https://cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/projects.locations/evaluateInstances#summarizationhelpfulnessinput)
- [Summarization Verbosity](https://cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/projects.locations/evaluateInstances#summarizationverbosityinput)

## Installation

```posix-terminal
npm i --save @genkit-ai/vertexai
```

If you want to locally run flows that use this plugin, you also need the
[Google Cloud CLI tool](https://cloud.google.com/sdk/docs/install) installed.

## Configuration

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { vertexAI } from '@genkit-ai/vertexai';

export default configureGenkit({
  plugins: [
    vertexAI({ projectId: 'your-cloud-project', location: 'us-central1' }),
  ],
  // ...
});
```

The plugin requires you to specify your Google Cloud project ID, the
[region](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations)
to which you want to make Vertex API requests, and your Google Cloud project
credentials.

- You can specify your Google Cloud project ID either by setting `projectId` in
  the `vertexAI()` configuration or by setting the `GCLOUD_PROJECT` environment
  variable. If you're running your flow from a Google Cloud environment (Cloud
  Functions, Cloud Run, and so on), `GCLOUD_PROJECT` is automatically set to the
  project ID of the environment.

- You can specify the API location either by setting `location` in the
  `vertexAI()` configuration or by setting the `GCLOUD_LOCATION` environment
  variable.

- To provide API credentials, you need to set up Google Cloud Application
  Default Credentials.

  1.  To specify your credentials:

      - If you're running your flow from a Google Cloud environment (Cloud
        Functions, Cloud Run, and so on), this is set automatically.

      - On your local dev environment, do this by running:

        ```posix-terminal
        gcloud auth application-default login
        ```

      - For other environments, see the [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc)
        docs.

  1.  In addition, make sure the account is granted the Vertex AI User IAM role
      (`roles/aiplatform.user`). See the Vertex AI [access control](https://cloud.google.com/vertex-ai/generative-ai/docs/access-control)
      docs.

## Usage

### Generative AI Models

This plugin statically exports references to its supported generative AI models:

```js
import { generate } from '@genkit-ai/ai';
import { geminiPro, geminiProVision, imagen2 } from '@genkit-ai/vertexai';
```

You can use these references to specify which model `generate()` uses:

```js
const llmResponse = await generate({
  model: geminiPro,
  prompt: 'What should I do when I visit Melbourne?',
});
```

This plugin also statically exports a reference to the Gecko text embedding
model:

```js
import { embed } from '@genkit-ai/ai/embedder';
import { textEmbeddingGecko } from '@genkit-ai/vertexai';
```

You can use this reference to specify which embedder an indexer or retriever
uses. For example, if you use Chroma DB:

```js
configureGenkit({
  plugins: [
    chroma([
      {
        embedder: textEmbeddingGecko,
        collectionName: 'my-collection',
      },
    ]),
  ],
});
```

Or you can generate an embedding directly:

```js
// import { embed, EmbedderArgument } from '@genkit-ai/ai/embedder';
const embedding = await embed({
  embedder: textEmbeddingGecko,
  content: 'How many widgets do you have in stock?',
});
```

#### Anthropic Claude 3 on Vertex AI Model Garden

If you have access to Claude 3 models ([haiku](https://console.cloud.google.com/vertex-ai/publishers/anthropic/model-garden/claude-3-haiku), [sonnet](https://console.cloud.google.com/vertex-ai/publishers/anthropic/model-garden/claude-3-sonnet) or [opus](https://console.cloud.google.com/vertex-ai/publishers/anthropic/model-garden/claude-3-opus)) in Vertex AI Model Garden you can use them with Genkit.

Here's sample configuration for enabling Vertex AI Model Garden models:

```js
import {
  vertexAI,
  claude3Haiku,
  claude3Sonnet,
  claude3Opus,
} from '@genkit-ai/vertexai';

export default configureGenkit({
  plugins: [
    vertexAI({
      location: 'us-central1',
      modelGardenModels: [claude3Haiku, claude3Sonnet, claude3Opus],
    }),
  ],
});
```

Then use them as regular models:

```js
import { generate } from '@genkit-ai/ai';

const llmResponse = await generate({
  model: claude3Sonnet,
  prompt: 'What should I do when I visit Melbourne?',
});
```

### Evaluators

To use the evaluators from Vertex AI Rapid Evaluation, add an `evaluation` block to your `vertexAI` plugin configuration.

```js
import { vertexAI, VertexAIEvaluationMetricType } from '@genkit-ai/vertexai';

export default configureGenkit({
  plugins: [
    vertexAI({
      projectId: 'your-cloud-project',
      location: 'us-central1',
      evaluation: {
        metrics: [
          VertexAIEvaluationMetricType.SAFETY,
          {
            type: VertexAIEvaluationMetricType.ROUGE,
            metricSpec: {
              rougeType: 'rougeLsum',
            },
          },
        ],
      },
    }),
  ],
  // ...
});
```

The configuration above adds evaluators for the `Safety` and `ROUGE` metrics. The example shows two approaches- the `Safety` metric uses the default specification, whereas the `ROUGE` metric provides a customized specification that sets the rouge type to `rougeLsum`.

Both evaluators can be run using the `genkit eval:run` command with a compatible dataset: that is, a dataset with `output` and `reference` fields. The `Safety` evaluator can also be run using the `genkit eval:flow -e vertexai/safety` command since it only requires an `output`.
