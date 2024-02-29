# Evaluation

Genkit's powerful observability provide insight into the runtime state of your LLM-powered application, which can provide evaluation tooling all the necessary data to evaluate the quality of LLM responses. The data that can be extracted from runtime is not limited to input and output of the flow, but we can also give you access to input and outputs of any intermediate step. For example, if you have a RAG flow we can extract the set of documents that was returned by the retriever so that you can evaluate the quality of your retriever while it runs in the context of the flow.

There are several of different ways to approach evaluation, we're actively working on it, but for now you can:

```
npx genkit eval:exportData myFlow
```

The exported data will be in a HuggingFace Dataset format that you can use with other open-source evaluation frameworks.

If you want to try this out, see rag sample in the samples folder.
