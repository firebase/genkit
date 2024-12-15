# Evaluation

Evaluations are a form of testing that helps you validate the responses of your LLM
and ensure they meet your quality standards.

Firebase Genkit supports third-party evaluation tools through plugins, paired
with powerful observability features that provide insight into the runtime state
of your LLM-powered applications. Genkit tooling helps you automatically extract
data including inputs, outputs, and information from intermediate steps to
evaluate the end-to-end quality of LLM responses as well as understand the
performance of your system's building blocks.

### Types of evaluations

Genkit supports two types of evaluations:

1. **Inference-based evaluation**: In this type of evaluation, a system is run on a collection of pre-determined inputs and the corresponding outputs are assessed for quality. 
    
    This is the most common evaluation type, suitable for most use cases. This approach tests the actual output of a system for each evaluation run.

    The quality assessment can be done manually by visually inspecting the results or automated by using an evaluation metric. 

2. **Raw evaluation**: This type of evaluation directly assesses the quality of inputs without any inference. This approach typically is used with automated evaluation using metrics. All required fields for evaluation (`context`, `output`) must be present in the input dataset. This is useful when you have data coming from an external source (eg: collected from your production traces) and you simply want to have an objective measurement of the quality of the collected data.

    We will cover more on this approach in our Advanced section below.

Let us now take a look at how we can do inference-based evaluations using Genkit.

## Quick start

### Setup
1. Use an existing Genkit app or create a new one by following our [Getting started](get-started) guide.
2. Add the following code to define a simple RAG application to evaluate. For this guide, we will use a dummy retriever that always return the same documents.

```js
import { genkit, z, Document } from "genkit";
import {
  googleAI,
  gemini15Flash,
  gemini15Pro,
} from "@genkit-ai/googleai";

// Initialize Genkit
export const ai = genkit ({
  plugins: [
    googleAI(),
  ]
});

// Dummy retriever that always returns the same docs
export const dummyRetriever = ai.defineRetriever(
  {
    name: "dummyRetriever",
  },
  async (i) => {
    const facts = [
      "Dog is man's best friend", 
      "Dogs have evolved and were domesticated from wolves",
    ];
    // Just return facts as documents.
    return { documents: facts.map((t) => Document.fromText(t)) };
  }
);

// A simple question answering flow
export const qaFlow = ai.defineFlow({
    name: 'qaFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (query) => {
    const factDocs = await ai.retrieve({
      retriever: dummyRetriever,
      query,
      options: { k: 2 },
    });

    const llmResponse = await ai.generate({
      model: gemini15Flash,
      prompt: `Answer this question with the given context ${query}`,
      docs: factDocs,
    });
    return llmResponse.text;
  }
);
```

3. (Optional) Add evaluation metrics to your application to use while evaluating. In this guide, we will use the `MALICIOUSNESS` metric from the `genkitEval` plugin.

```js
import { genkitEval, GenkitMetric } from "@genkit-ai/evaluator";
import { gemini15Pro } from "@genkit-ai/googleai";

export const ai = genkit ({
  plugins: [
    ...
    // Add this plugin to your Genkit initialization block
    genkitEval({
      judge: gemini15Pro,
      metrics: [GenkitMetric.MALICIOUSNESS],
    }),
  ]
});
```

**Note:** The configuration above requires installing the `@genkit-ai/evaluator` package.

```posix-terminal
  npm install @genkit-ai/evaluator
```

4. Start your Genkit application

```posix-terminal
genkit start -- <command to start your app>
```

### Create a dataset

Let us create a dataset to define the examples we want to use for evaluating our flow. 

1. Go to the Dev UI at `http://localhost:4000` and click the **Datasets** button to open the Datasets page.

2. Click on the **Create Dataset** button to open the create dataset dialog.

    a. Provide a `datasetId` to your new dataset. In this guide, we will be using `myFactsQaDataset`.

    b. Select `Flow` dataset type.

    c. Leave the validation target field empty and click **Save**

3. You will be redirected to your new dataset page. This dataset is empty, let us add a few examples to our dataset.

    a. Click the **Add example** button to open the example editor panel.

    b. Only the `input` field is required. Enter `"Who is man's best friend?"` in the input field, and click **Save**. You will see that this example has been added to your dataset.

    c. Repeat steps (a) and (b) a couple more times to add more examples. In this guide, we add the following example inputs to the dataset:

    ```
    "Can I give milk to my cats?"
    "From which animals did dogs evolve from?"
    ```

    By the end of this step, your dataset will have 3 examples in it, with the values mentioned above.

### Run evaluation and view results

Now we're ready to evaluate our flow. Visit the `Evaluations` tab in the Dev UI and click the **Run new evaluation** button to get started.

1. Select the `Flow` radio button, as we want to evaluate a flow.

2. Select `qaFlow` as the target flow to evaluate.

3. Select `myFactsQaDataset` as the target dataset to use for evaluation.

4. (Optional) If you have installed an evaluator metric using Genkit plugins, you can see these metrics in this page. Select the metrics that you want to use with this evaluation run. This is entirely optional and omitting this step will return the results in the evaluation run, without any metrics associated with them.

5. Finally, click **Run evaluation** to start evaluation. Depending on the flow you're testing, this may take a while. Once the evaluation is complete, you will see a success message with a link to view the results. Click on the link to go to the Evaluation details page.

You can see the details of your evaluation run on this page, including original input, extracted context and metrics (if any). 

<!-- TODO, more convincing conclusion here? -->

## Core concepts

### Terminology

- **Evaluation**: An evaluation is a process by which the quality of performance of a system is assessed. In Genkit, such a system is usually a Genkit primitive, such as a flow or a model. An evaluation can be automated or manual (human evaluation).

- **Bulk inference** Inference is simply the act of running an input on a flow or model to get the corresponding output. Bulk inference involves performing inference on multiple inputs simultaneously.

- **Metric** An evaluation metric is a criteria on which an inference is scored. E.g.: accuracy, faithfulness, maliciousness, whether the output is in English, etc.

- **Dataset** A dataset is a collection of examples to use for inference-based evaluation. A dataset typically consists of `input` and optional `reference` fields. The `reference` field does not affect the inference step of evaluation but it is passed verbatim to any evaluation metrics. In Genkit, you can create a dataset through the Dev UI.

## Supported evaluators

### Genkit evaluators

Genkit includes a small number of native evaluators, inspired by RAGAS, to help
you get started:

*   Faithfulness -- Measures the factual consistency of the generated answer against the given context
*   Answer Relevancy -- Assesses how pertinent the generated answer is to the given prompt
*   Maliciousness -- Measures whether the generated output intends to deceive, harm, or exploit

### Evaluator plugins

Genkit supports additional evaluators through plugins like the VertexAI Rapid Evaluators via the [VertexAI Plugin](./plugins/vertex-ai#evaluators).

## Advanced use

### Evaluation using the CLI

Genkit CLI provides a rich API for performing evaluations. This is especially useful in environments where the Dev UI is not available (e.g. in a CI/CD workflow). 

Genkit CLI provides 3 main evaluation commands: `eval:flow`, `eval:extractData` and `eval:run`.

#### `eval:flow` command

The `eval:flow` command runs inference-based evaluation on an input dataset. This dataset may be provided either as a JSON file or by referencing an existing dataset in your Genkit runtime. 
<!-- Is runtime the right word? -->

```posix-terminal
# Referencing an existing dataset
genkit eval:flow qaFlow --input myFactsQaDataset

# or, using a dataset from a file
genkit eval:flow qaFlow --input testInputs.json
```

Note: Make sure that you start your genkit app before running these CLI commands.
```posix-terminal
genkit start -- <command to start your app>
```

Here, `testInputs.json` should be an array of objects containing an `input` field and an optional `reference` field, like below:

```json
[
  {
    "input": "What is the French word for Cheese?",
  },
  {
    "input": "What green vegetable looks like cauliflower?",
    "reference": "Broccoli"
  }
]
```

If your flow requires auth, you may specify it using the `--auth` argument:

```posix-terminal
genkit eval:flow qaFlow --input testInputs.json --auth "{\"email_verified\": true}"
```

By default, the `eval:flow` and `eval:run` use all available metrics for evaluation. To run on a subset of the configured evaluators, use the `--evaluators` flag and
provide a comma-separated list of evaluators by name:

```posix-terminal
genkit eval:flow qaFlow --input testInputs.json --evaluators=genkit/faithfulness,genkit/answer_relevancy
```
You can view the results of your evaluation run in the Dev UI at `localhost:4000/evaluate`.

#### `eval:extractData` and `eval:run` commands

To support *raw evaluation*, Genkit provides tools to extract data from traces and run evaluation metrics on extracted data. This is useful, for e.g., if you are using a
different framework for evaluation or if you are collecting inferences from a different environment to test locally for output quality. 

You can batch run your Genkit flow and add a unique label to the run which then
will be used to extract an *evaluation dataset*. An evaluation dataset is a collection of inputs for evaluation metrics, *without* running any prior inference.

Run your flow over your test inputs:

```posix-terminal
genkit flow:batchRun qaFlow testInputs.json --label firstRunSimple
```

Extract the evaluation data:

```posix-terminal
genkit eval:extractData qaFlow --label firstRunSimple --output factsEvalDataset.json
```

The exported data has a format different from the dataset format you've seen earlier. This is because this data is intended to be used with evaluation metrics directly, without any inference step. Here is the syntax of the extracted data.

```json
Array<{
  "testCaseId": string,
  "input": any,
  "output": any,
  "context": any[],
  "traceIds": string[],
}>;
```

The data extractor will automatically locate retrievers and add the produced docs to the context array. You can run evaluation metrics on this extracted dataset using the `eval:run` command.

```posix-terminal
genkit eval:run factsEvalDataset.json
```

By default, `eval:run` will run against all configured evaluators, and like `eval:flow`, results for `eval:run` will appear in the evaluation page of Developer UI, located at `localhost:4000/evaluate`.

### Custom extractors

<!-- TOOD: Any caveats on where this approach does not work (ES5 or something?)  -->

Genkit provides reasonable default logic for extracting the necessary fields (`input`, `output` and `context`) 
while doing an evaluation. However you may find that you need more control over the extraction logic for these fields. Genkit supports customs extractors to achieve this. You can provide custom extractors to be used in `eval:extractData` and
`eval:flow` commands.

Let us first introduce an auxilary step in our `qaFlow` example:

```js
export const qaFlow = ai.defineFlow({
    name: 'qaFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (query) => {
    const factDocs = await ai.retrieve({
      retriever: dummyRetriever,
      query,
      options: { k: 2 },
    });
    const factDocsModified = await run('factModified', async () => {
        // Let us only facts that are considered silly. This is a hypothetical step
        // for demo purposes, you may perform any arbitrary task inside a step
        // and reference it in custom extractors.
        //
        // Assume you have a method that checks if a fact is silly
        return factDocs.filter(d => isSillyFact(d.text));
    });

    const llmResponse = await ai.generate({
      model: gemini15Flash,
      prompt: `Answer this question with the given context ${query}`,
      docs: factDocs,
    });
    return llmResponse.text;
  }
);
```

Now let us configure a custom extractor to use the output of the `factModified` step when evaluating this flow.

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
      actionRef: '/flow/qaFlow',
      extractors: {
        context: { outputOf: 'factModified' },
      },
    },
  ],
};
```

This config overrides the default extractors of Genkit's tooling, specifically changing what is considered as as `context` when evaluating this flow.

You can run evaluation again and you will see that context is now populated as the output of the step.

```posix-terminal
genkit eval:flow qaFlow --input testInputs.json
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
        function that accepts a Genkit trace and returns `any` type, and specify
        the extraction logic inside this function. Refer to
        `genkit/genkit-tools/common/src/types/trace.ts` for the exact TraceData
        schema.

**Note:** The extracted data for all these extractors will be the type corresponding to the extractor. For example, if you use context: `{ outputOf: 'foo-step' }` and `foo-step` returns an array of objects, the extracted context will also be an array of objects.. 

### Synthesizing test data using an LLM

Here's an example flow that uses a PDF file to generate potential user questions.

```ts
import { genkit, run, z } from "genkit";
import { googleAI, gemini15Flash } from "@genkit-ai/googleai";
import { chunk } from "llm-chunk"; // npm i llm-chunk
import path from "path";
import { readFile } from "fs/promises";
import pdf from "pdf-parse"; // npm i pdf-parse

const ai = genkit({ plugins: [googleAI()] });

const chunkingConfig = {
  minLength: 1000, // number of minimum characters into chunk
  maxLength: 2000, // number of maximum characters into chunk
  splitter: "sentence", // paragraph | sentence
  overlap: 100, // number of overlap chracters
  delimiters: "", // regex for base split method
} as any;

async function extractText(filePath: string) {
  const pdfFile = path.resolve(filePath);
  const dataBuffer = await readFile(pdfFile);
  const data = await pdf(dataBuffer);
  return data.text;
}

export const synthesizeQuestions = ai.defineFlow(
  {
    name: "synthesizeQuestions",
    inputSchema: z.string().describe("PDF file path"),
    outputSchema: z.array(z.string()),
  },
  async (filePath) => {
    filePath = path.resolve(filePath);
    // `extractText` loads the PDF and extracts its contents as text.
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
