
# Evaluation

Genkit's powerful observability features provide insight into the runtime state
of your LLM-powered application, which can provide evaluation tooling with all
the necessary data to evaluate the quality of LLM responses. The data that can
be extracted from runtime is not limited to input and output of the flow, but
can also give you access to input and outputs of any intermediate step. For
example, if you have a RAG flow you can extract the set of documents that was
returned by the retriever so that you can evaluate the quality of your retriever
while it runs in the context of the flow.

Genkit supports third party evaluation plugins, ex:

```js
import { RagasMetric, ragas } from '@genkit-ai/plugin-ragas';

export default configureGenkit({
  plugins: [
    ragas({ judge: geminiPro, metrics: [RagasMetric.CONTEXT_UTILIZATION] }),
  ],
  // ...
});
```

Once installed, the evaluation plugins provide evalution metrics to the Genkit framework which can be used with the Genkit evaluation tooling.

Start by defining a set of inputs that you want to use as a test dataset. For example:

```json
[
  "How old is Spongebob?",
  "Where does Spongebob lives?",
  "Does Spongebob have any friends?",
]
```

Below you can see an example of how an LLM can help you generate the test dataset.

You can then use `eval:flow` command to evaluate your flow against the test dataset.

```posix-terminal
genkit eval:flow spongebobQA --input testQuestions.json --output eval-result.json
```

You can then see evaluation results in the output json file.

## Advanced use

`eval:flow` is a convenient way quickly evaluate the flow, but sometimes you might need more control over evaluation steps. You can perform all the step that `eval:flow` semi-manually.

You can batch run your RAG flow and label the runs with a unique label which then will be used to extract evaluation data.

```posix-terminal
npx genkit flow:batchRun myRagFlow test_inputs.json --output flow_outputs.json --label eval123
```

Extract the evaluation data:

```posix-terminal
npx genkit eval:extractData myRagFlow --label eval123 --output eval123_dataset.json
```

The exported data will be in a HuggingFace Dataset format that you can use with
other open-source evaluation frameworks. The data extractor will automatically
locate retrievers and add the produced docs to the dataset as context.

You can the then run the installed evaluators on the dataset:

```posix-terminal
npx genkit eval:run eval123_dataset.json --output eval123-evalresult.json
```

The evaluator will automatically use the evaluators that you have installed in
your config.


### Synthesizing test data using an LLM

Here's an example flow which will use a PDF file to generate possible questions users might be asking about it.

```js
export const synthesizeQuestions = flow(
  {
    name: 'synthesizeQuestions',
    input: z.string().describe('PDF file path'),
    output: z.array(z.string()),
  },
  async (filePath) => {
    filePath = path.resolve(filePath);
    const pdfTxt = await run('extract-text', () => extractText(filePath));

    const chunks = await run('chunk-it', async () =>
      chunk(pdfTxt, chunkingConfig)
    );

    const questions: string[] = [];
    for (var i = 0; i < chunks.length; i++) {
      const qResponse = await generate({
        model: geminiPro,
        prompt: {
          text: `Generate one question about the text below: ${chunks[i]}`,
        },
      });
      questions.push(qResponse.text());
    }
    return questions;
  }
);
```

You can then use this command to export the data into a file and use for evaluation.

```posix-terminal
genkit flow:run synthesizeQuestions '"35650.pdf"' --output synthesizedQuestions.json
```
