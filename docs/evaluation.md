# Evaluation

Genkit's powerful observability provide insight into the runtime state of your LLM-powered application, which can provide evaluation tooling all the necessary data to evaluate the quality of LLM responses. The data that can be extracted from runtime is not limited to input and output of the flow, but we can also give you access to input and outputs of any intermediate step. For example, if you have a RAG flow we can extract the set of documents that was returned by the retriever so that you can evaluate the quality of your retriever while it runs in the context of the flow.

There are several different ways to approach evaluation, we're actively working on it, but for now you can:

Produce a test dataset of inputs for the RAG flow. Ex:

```
[
  "How old is Spongebob?",
  "Where does Spongebob lives?",
  "Does Spongebob have any friends?",
]
```

You can then batch run your RAG flag and label the runs with a unique label which then will be used to extract evaluation data"

```
genkit flow:batchRun myRagFlow test_inputs.json --output flow_outputs.json --label eval123
```

Extract the evaluation data:

```
genkit eval:extractData myRagFlow --label eval123 --output eval123_dataset.json
```

The exported data will be in a HuggingFace Dataset format that you can use with other open-source evaluation frameworks. The data extractor will automatically locate retrievers and add the produced docs to the dataset as context.

You can the then run the installed evaluators on the dataset:

```
genkit eval:run eval123_dataset.json --output eval123-evalresult.json
```

The evaluator will automatically use the evaluators that you have installed in your config. For example:

```javascript
import { RagasMetric, ragas } from '@genkit-ai/plugin-ragas';

export default configureGenkit({
  plugins: [
    ragas({ judge: geminiPro, metrics: [RagasMetric.CONTEXT_PRECISION] }),
  ],
  // ...
});
```