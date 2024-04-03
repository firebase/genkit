# Evaluation (Preview)

NOTE: _Evaluation in Genkit is currently in early preview_ with a limited set of available evaluation metrics. You can try out the current experience by following the documentation below. If you run into any issues or have suggestions for improvements, please [file an issue](http://github.com/google/genkit/issues). We would love to see your feedback as we refine the evaluation experience!

Evaluations are a form of testing which helps you validate your LLM’s responses and ensure they meet your quality bar.

Genkit supports third-party evaluation tools through plugins, paired with powerful observability features which provide insight into the runtime state
of your LLM-powered applications. Genkit tooling helps you automatically extract data including inputs, outputs, and information from intermediate steps to evaluate the end-to-end quality of LLM responses as well as understand the performance of your system’s building blocks.

For example, if you have a RAG flow, Genkit will extract the set
of documents that was returned by the retriever so that you can evaluate the
quality of your retriever while it runs in the context of the flow as shown below with the RAGAS faithfulness and answer relevancy metrics:

```js
import { RagasMetric, ragas } from '@genkit-ai/plugin-ragas';

export default configureGenkit({
  plugins: [
    ragas({
      judge: geminiPro,
      metrics: [RagasMetric.FAITHFULNESS, RagasMetric.ANSWER_RELEVANCY],
    }),
  ],
  // ...
});
```

Once installed, evaluation plugins provide metrics to the Genkit framework that
you can use with Genkit's evaluation tooling. For now, and since evals are still an early preview, we only support a small number of RAGAS metrics including: Faithfulness, Answer Relevancy, and Context Utilization.

Start by defining a set of inputs that you want to use as a test dataset called `testQuestions.json`:

```json
[
  "How old is Spongebob?",
  "Where does Spongebob lives?",
  "Does Spongebob have any friends?"
]
```

You can then use `eval:flow` command to evaluate your flow against the test
cases provided in `testQuestions.json`.

```posix-terminal
genkit eval:flow spongebobQA --input testQuestions.json
```

You can then see evaluation results in the DevUI by running:

```posix-terminal
genkit start
```

Then navigate to `localhost:4000/evaluate`.

Alternatively, you can provide an output file to inspect the output in a json file.

```posix-terminal
genkit eval:flow spongebobQA --input testQuestions.json --output eval-result.json
```

Note: Below you can see an example of how an LLM can help you generate the test
cases.

## Advanced use

`eval:flow` is a convenient way quickly evaluate the flow, but sometimes you
might need more control over evaluation steps. You can perform all the step that
`eval:flow` performs semi-manually.

You can batch run your RAG flow and label the runs with a unique label which
then will be used to extract evaluation data.

```posix-terminal
npx genkit flow:batchRun myRagFlow test_inputs.json --output flow_outputs.json --label customLabel
```

Extract the evaluation data:

```posix-terminal
npx genkit eval:extractData myRagFlow --label customLabel --output customLabel_dataset.json
```

The exported data will be output as a json file with each testCase in the following format:

```json
[
  {
    "testCaseId": string,
    "input": string,
    "output": string,
    "context": array of strings,
    "traceIds": array of strings,
  }
]
```

The data extractor will automatically locate retrievers and add the produced docs to the dataset as context. By default, `eval:run` will run against all configured evaluators, and like `eval:flow`, results for `eval:run` will appear in the evaluation page of DevUI, located at `localhost:4000/evaluate`.

```posix-terminal
npx genkit eval:run customLabel_dataset.json
```

To output to a different location, use the `--output` flag.

```posix-terminal
genkit eval:flow spongebobQA --input testQuestions.json --output customLabel_evalresult.json
```

To run on a subset of the configured evaluators, use the `--evaluators` flag and provide a comma separated list of evaluators by name:

```posix-terminal
npx genkit eval:run customLabel_dataset.json --evaluators=ragas/faithfulness,ragas/answer_relevancy
```

### Synthesizing test data using an LLM

Here's an example flow that uses a PDF file to generate possible questions
users might be asking about it.

```js
export const synthesizeQuestions = defineFlow(
  {
    name: 'synthesizeQuestions',
    inputSchema: z.string().describe('PDF file path'),
    outputSchema: z.array(z.string()),
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

You can then use this command to export the data into a file and use for
evaluation.

```posix-terminal
genkit flow:run synthesizeQuestions '"my_input.pdf"' --output synthesizedQuestions.json
```
