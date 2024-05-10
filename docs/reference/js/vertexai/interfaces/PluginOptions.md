# Interface: PluginOptions

## Properties

| Property | Type | Description |
| :------ | :------ | :------ |
| `evaluation?` | \{ `"metrics"`: `VertexAIEvaluationMetric`[]; \} | Configure Vertex AI evaluators |
| `evaluation.metrics` | `VertexAIEvaluationMetric`[] | - |
| `googleAuth?` | `GoogleAuthOptions`\<`JSONClient`\> | Provide custom authentication configuration for connecting to Vertex AI. |
| `location` | `string` | The Google Cloud region to call. |
| `modelGardenModels?` | `ModelReference`\<`any`\>[] | - |
| `projectId?` | `string` | The Google Cloud project id to call. |
