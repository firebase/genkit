# Evaluation

Evaluations are a form of testing that helps you validate your LLM's responses
and ensure they meet your quality bar.

Firebase Genkit supports third-party evaluation tools through plugins, paired
with powerful observability features that provide insight into the runtime state
of your LLM-powered applications. Genkit tooling helps you automatically extract
data including inputs, outputs, and information from intermediate steps to
evaluate the end-to-end quality of LLM responses as well as understand the
performance of your system's building blocks.

For example, if you have a RAG flow, Genkit will extract the set of documents
that was returned by the retriever so that you can evaluate the quality of your
retriever while it runs in the context of the flow as shown below with the
Genkit faithfulness and answer relevancy metrics:

```ts
import { genkit } from 'genkit';
import { genkitEval, GenkitMetric } from '@genkit-ai/evaluator';
import { vertexAI, textEmbedding004, gemini15Pro } from '@genkit-ai/vertexai';

const ai = genkit({
  plugins: [
    vertexAI(),
    genkitEval({
      judge: gemini15Pro, // Use a powerful LLM as judge
      metrics: [GenkitMetric.MALICIOUSNESS, GenkitMetric.ANSWER_RELEVANCY],
      embedder: textEmbedding004, // GenkitMetric.ANSWER_RELEVANCY requires an embedder
    }),
  ],
  // ...
});

// Define a simple menu suggestion flow
export const menuSuggestionFlow = ai.defineFlow(
  {
    name: "menuSuggestionFlow",
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (query) => {
    const llmResponse = await ai.generate({
      model: gemini15Flash,
      prompt: `Suggest a menu item using ${query}`,
    });
    return llmResponse.text;
  }
);
```

**Note:** The configuration above requires installing the `genkit`,
`@genkit-ai/googleai`, `@genkit-ai/evaluator` and `@genkit-ai/vertexai`
packages.

```posix-terminal
  npm install @genkit-ai/evaluator @genkit-ai/vertexai
```

Start by defining a set of inputs that you want to use as an input dataset
called `testInputs.json`. This input dataset represents the test cases you will
use to generate output for evaluation.

```json
[
  {
    "input": "What is the French word for Cheese?"
  },
  {
    "input": "What green vegetable looks like cauliflower?"
  }
]
```

If the evaluator requires a reference output for evaluating a flow, you can pass both 
input and reference output using this format instead:

```json
[
  {
    "input": "What is the French word for Cheese?",
    "reference": "Fromage"
  },
  {
    "input": "What green vegetable looks like cauliflower?",
    "reference": "Broccoli"
  }
]
```

Note that you can use any JSON data type in the input JSON file. Genkit will pass them along with the same data type to your flow.

You are now ready to start evaluating your flow. Begin by starting up your app with `genkit start`:

```posix-terminal
genkit start -- <command to start your app>
```

You can then use the `eval:flow` command to evaluate your flow against the test
cases provided in `testInputs.json`.

```posix-terminal
genkit eval:flow menuSuggestionFlow --input testInputs.json
```

If your flow requires auth, you may specify it using the `--auth` argument:

```posix-terminal
genkit eval:flow menuSuggestionFlow --input testInputs.json --auth "{\"email_verified\": true}"
```

To run on a subset of the configured evaluators, use the `--evaluators` flag and
provide a comma-separated list of evaluators by name:

```posix-terminal
genkit eval:flow menuSuggestionFlow --input testInputs.json --evaluators=genkit/faithfulness,genkit/answer_relevancy
```

Then navigate to `localhost:4000/evaluate` to view your evaluation results.

Alternatively, you can provide an output file to inspect the output in a JSON
file.

```posix-terminal
genkit eval:flow menuSuggestionFlow --input testInputs.json --output eval-result.json
```

**Note:** Below you can see an example of how an LLM can help you generate the
test cases.

## Supported evaluators

### Genkit evaluators

Genkit includes a small number of native evaluators, inspired by RAGAS, to help
you get started:

*   Faithfulness
*   Answer Relevancy
*   Maliciousness

### Evaluator plugins

Genkit supports additional evaluators through plugins like the VertexAI Rapid Evaluators via the [VertexAI Plugin](./plugins/vertex-ai#evaluators).

## Advanced use

`eval:flow` is a convenient way to quickly evaluate the flow, but sometimes you
might need more control over evaluation steps. This may occur if you are using a
different framework and already have some output you would like to evaluate. You
can perform all the steps that `eval:flow` performs semi-automaticaly.

You can batch run your Genkit flow and add a unique label to the run which then
will be used to extract an evaluation dataset (a set of inputs, outputs, and
contexts).

Run the flow over your test inputs:

```posix-terminal
genkit flow:batchRun menuSuggestionFlow testInputs.json --label myFavoriteFoods
```

Extract the evaluation data:

```posix-terminal
genkit eval:extractData menuSuggestionFlow --label myFavoriteFoods --output myFavoriteFoods_dataset.json
```

The exported data will be output as a JSON file with each testCase in the
following format:

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

The data extractor will automatically locate retrievers and add the produced
docs to the context array. You can run evaluation metrics on this extracted dataset using the `eval:run` 
command.

```posix-terminal
genkit eval:run myFavoriteFoods_dataset.json
```

By default, `eval:run` will run against all
configured evaluators, and like `eval:flow`, results for `eval:run` will appear
in the evaluation page of Developer UI, located at `localhost:4000/evaluate`.

### Custom extractors

You can also provide custom extractors to be used in `eval:extractData` and
`eval:flow` commands. Custom extractors allow you to override the default
extraction logic giving you more power in creating datasets and evaluating them.

Let us first introduce an auxilary step in our `menuSuggestionFlow` example:

```js
export const menuSuggestionFlow = ai.defineFlow(
  {
    name: "menuSuggestionFlow",
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (query) => {
    const allergyItems = await run('allergyItems', async () => {
        // You are allergic to these!
        //
        // This step is for demo purposes, think of it as something auxillary
        // to your model input, eg: an API call that you would 
        // include in the prompt, etc. 
        return ["Shirmp", "Eggs", "Peanuts"];
    });
    const llmResponse = await ai.generate({
      model: gemini15Flash,
      prompt: `Suggest a menu item using ${query}. Assume that I am allergic to these ingredients ${allergyItems.join(', ')}`,
    });
    return llmResponse.text;
  }
);
```

Now let us configure a custom extractor to use the output of the `allergyItems` step when evaluating this flow.

To configure custom extractors, add a tools config file named
`genkit-tools.conf.js` to your project root if you don't have one already.

```posix-terminal
cd /path/to/your/genkit/app

touch genkit-tools.conf.js
```

In the tools config file, add the following code:

```js
module.exports = {
  evaluators: [
    {
      actionRef: '/flow/menuSuggestionFlow',
      extractors: {
        context: { outputOf: 'allergyItems' },
      },
    },
  ],
};
```

This config overrides the default extractors of Genkit's tooling, specifically changing what is considered as as `context` when evaluating this flow.

You can run evaluation again and you will see that context is now populated as the output of the step.

```posix-terminal
genkit eval:flow menuSuggestionFlow --input testInputs.json
```

The specification of the evaluation extractors is as follows:

*   `evaluators` field accepts an array of EvaluatorConfig objects, which are
    scoped by `flowName`
*   `extractors` is an object that specifies the extractor overrides. The
    current supported keys in `extractors` are `[input, output, context]`. The
    acceptable value types are:
    *   `string` - this should be a step name, specified as a string. The output
        of this step is extracted for this key.
    *   `{ inputOf: string }` or `{ outputOf: string }` - These objects
        represent specific channels (input or output) of a step. For example, `{
        inputOf: 'foo-step' }` would extract the input of step `foo-step` for
        this key.
    *   `(trace) => string;` - For further flexibility, you can provide a
        function that accepts a Genkit trace and returns a `string`, and specify
        the extraction logic inside this function. Refer to
        `genkit/genkit-tools/common/src/types/trace.ts` for the exact TraceData
        schema.

**Note:** The extracted data for all these steps will be a JSON string. The
tooling will parse this JSON string at the time of evaluation automatically. If
providing a function extractor, make sure that the output is a valid JSON
string. For example: `"Hello, world!"` is not valid JSON; `"\"Hello, world!\""`
is valid.

### Synthesizing test data using an LLM

Here's an example flow that uses a PDF file to generate possible questions users
might be asking about it.

```ts
import { genkit, run, z } from "genkit";
import { googleAI, gemini15Flash } from "@genkit-ai/googleai";
import { chunk } from "llm-chunk";
import path from 'path';

const ai = genkit({ plugins: [googleAI()] });

const chunkingConfig = {
  minLength: 1000, // number of minimum characters into chunk
  maxLength: 2000, // number of maximum characters into chunk
  splitter: 'sentence', // paragraph | sentence
  overlap: 100, // number of overlap chracters
  delimiters: '', // regex for base split method
} as any;

export const synthesizeQuestions = ai.defineFlow(
  {
    name: "synthesizeQuestions",
    inputSchema: z.string().describe("PDF file path"),
    outputSchema: z.array(z.string()),
  },
  async (filePath) => {
    filePath = path.resolve(filePath);
    // `extractText` loads the PDF and extracts its contents as text.
    // See our RAG documentation for more details. 
    const pdfTxt = await run("extract-text", () => extractText(filePath));

    const chunks = await run("chunk-it", async () =>
      chunk(pdfTxt, chunkingConfig)
    );

    const questions: string[] = [];
    for (var i = 0; i < chunks.length; i++) {
      const qResponse = await ai.generate({
        model: gemini15Flash,
        prompt: {
          text: `Generate one question about the text below: ${chunks[i]}`,
        },
      });
      questions.push(qResponse.text);
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
