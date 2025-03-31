# Writing a Genkit Evaluator

You can extend Genkit to support custom evaluation, using either
an LLM as a judge, or by programmatic (heuristic) evaluation.

## Evaluator definition

Evaluators are functions that assess an LLM's response. There are two main
approaches to automated evaluation: heuristic evaluation and LLM-based
evaluation. In the heuristic approach, you define a deterministic function.
By contrast, in an LLM-based assessment, the content is fed back to an LLM,
and the LLM is asked to score the output according to criteria set in a
prompt.

The `ai.defineEvaluator` method, which you use to define an
evaluator action in Genkit, supports either approach. This
document explores a couple of examples of how to use this
method for heuristic and LLM-based evaluations. 

### LLM-based Evaluators

An LLM-based evaluator leverages an LLM to evaluate
the `input`, `context`, and `output` of your generative AI
feature.

LLM-based evaluators in Genkit are made up of 3 components:

- A prompt
- A scoring function
- An evaluator action

#### Define the prompt

For this example, the evaluator leverages an LLM to determine whether a
food (the `output`) is delicious or not. First, provide context to the LLM,
then describe what you want it to do, and finally, give it a few examples
to base its response on.

Genkit’s `definePrompt` utility provides an easy way to define prompts with
input and output validation. The following code is an example of
setting up an evaluation prompt with `definePrompt`.

```ts
import { z } from "genkit";

const DELICIOUSNESS_VALUES = ['yes', 'no', 'maybe'] as const;

const DeliciousnessDetectionResponseSchema = z.object({
  reason: z.string(),
  verdict: z.enum(DELICIOUSNESS_VALUES),
});

function getDeliciousnessPrompt(ai: Genkit) {
  return  ai.definePrompt({
      name: 'deliciousnessPrompt',
      input: {
        schema: z.object({
          responseToTest: z.string(),
        }),
      },
      output: {
        schema: DeliciousnessDetectionResponseSchema,
      }
      prompt: `You are a food critic. Assess whether the provided output sounds delicious, giving only "yes" (delicious), "no" (not delicious), or "maybe" (undecided) as the verdict.

      Examples:
      Output: Chicken parm sandwich
      Response: { "reason": "A classic and beloved dish.", "verdict": "yes" }

      Output: Boston Logan Airport tarmac
      Response: { "reason": "Not edible.", "verdict": "no" }

      Output: A juicy piece of gossip
      Response: { "reason": "Metaphorically 'tasty' but not food.", "verdict": "maybe" }

      New Output: {% verbatim %}{{ responseToTest }} {% endverbatim %}
      Response:
      `
  });
}
```

#### Define the scoring function

Define a function that takes an example that includes `output` as
required by the prompt, and scores the result. Genkit testcases include
`input` as  a required field, with `output` and `context` as optional fields.
It is the  responsibility of the evaluator to validate that all fields
required for evaluation are present.

```ts
import { ModelArgument } from 'genkit';
import { BaseEvalDataPoint, Score } from 'genkit/evaluator';

/**
 * Score an individual test case for delciousness.
 */
export async function deliciousnessScore<
  CustomModelOptions extends z.ZodTypeAny,
>(
  ai: Genkit,
  judgeLlm: ModelArgument<CustomModelOptions>,
  dataPoint: BaseEvalDataPoint,
  judgeConfig?: CustomModelOptions
): Promise<Score> {
  const d = dataPoint;
  // Validate the input has required fields
  if (!d.output) {
    throw new Error('Output is required for Deliciousness detection');
  }

  // Hydrate the prompt and generate an evaluation result
  const deliciousnessPrompt = getDeliciousnessPrompt(ai);
  const response = await deliciousnessPrompt(
    {
      responseToTest: d.output as string,
    },
    {
      model: judgeLlm,
      config: judgeConfig,
    }
  );

  // Parse the output
  const parsedResponse = response.output;
  if (!parsedResponse) {
    throw new Error(`Unable to parse evaluator response: ${response.text}`);
  }

  // Return a scored response
  return {
    score: parsedResponse.verdict,
    details: { reasoning: parsedResponse.reason },
  };
}
```

#### Define the evaluator action

The final step is to write a function that defines the `EvaluatorAction`.

```ts
import { EvaluatorAction } from 'genkit/evaluator';

/**
 * Create the Deliciousness evaluator action.
 */
export function createDeliciousnessEvaluator<
  ModelCustomOptions extends z.ZodTypeAny,
>(
  ai: Genkit,
  judge: ModelArgument<ModelCustomOptions>,
  judgeConfig?: z.infer<ModelCustomOptions>
): EvaluatorAction {
  return ai.defineEvaluator(
    {
      name: `myCustomEvals/deliciousnessEvaluator`,
      displayName: 'Deliciousness',
      definition: 'Determines if output is considered delicous.',
      isBilled: true,
    },
    async (datapoint: BaseEvalDataPoint) => {
      const score = await deliciousnessScore(ai, judge, datapoint, judgeConfig);
      return {
        testCaseId: datapoint.testCaseId,
        evaluation: score,
      };
    }
  );
}
```

The `defineEvaluator` method is similar to other Genkit constructors like
`defineFlow` and `defineRetriever`. This method requires an `EvaluatorFn`
to be provided as a callback. The `EvaluatorFn` method accepts a
`BaseEvalDataPoint` object, which corresponds to a single entry in a
dataset under evaluation, along with an optional custom-options
parameter if specified. The function processes the datapoint and
returns an `EvalResponse` object. 

The Zod Schemas for `BaseEvalDataPoint` and `EvalResponse` are
as follows.

##### `BaseEvalDataPoint`

```ts
export const BaseEvalDataPoint = z.object({
  testCaseId: z.string(),
  input: z.unknown(),
  output: z.unknown().optional(),
  context: z.array(z.unknown()).optional(),
  reference: z.unknown().optional(),
  testCaseId: z.string().optional(),
  traceIds: z.array(z.string()).optional(),
});

export const EvalResponse = z.object({
  sampleIndex: z.number().optional(),
  testCaseId: z.string(),
  traceId: z.string().optional(),
  spanId: z.string().optional(),
  evaluation: z.union([ScoreSchema, z.array(ScoreSchema)]),
});
```
##### `ScoreSchema`

```ts
const ScoreSchema = z.object({
  id: z.string().describe('Optional ID to differentiate multiple scores').optional(),
  score: z.union([z.number(), z.string(), z.boolean()]).optional(),
  error: z.string().optional(),
  details: z
    .object({
      reasoning: z.string().optional(),
    })
    .passthrough()
    .optional(),
});
```

The `defineEvaluator` object lets the user provide a name, a user-readable
display name, and a definition for the evaluator. The display name and
definiton are displayed along with evaluation results in the Dev UI.
It also has an optional `isBilled` field that marks whether this evaluator
can result in billing (e.g., it uses a billed LLM or API). If an evaluator
is billed, the UI prompts the user for a confirmation in the CLI before
allowing them to run an evaluation. This step helps guard against
unintended expenses.

### Heuristic Evaluators

A heuristic evaluator can be any function used to evaluate the `input`, `context`,
or `output` of your generative AI feature.

Heuristic evaluators in Genkit are made up of 2 components:

- A scoring function
- An evaluator action

#### Define the scoring function

As with the LLM-based evaluator, define the scoring function. In this case,
the scoring function does not need a judge LLM.

```ts
import { BaseEvalDataPoint, Score } from 'genkit/evaluator';

const US_PHONE_REGEX =
  /[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4}/i;

/**
 * Scores whether a datapoint output contains a US Phone number.
 */
export async function usPhoneRegexScore(
  dataPoint: BaseEvalDataPoint
): Promise<Score> {
  const d = dataPoint;
  if (!d.output || typeof d.output !== 'string') {
    throw new Error('String output is required for regex matching');
  }
  const matches = US_PHONE_REGEX.test(d.output as string);
  const reasoning = matches
    ? `Output matched US_PHONE_REGEX`
    : `Output did not match US_PHONE_REGEX`;
  return {
    score: matches,
    details: { reasoning },
  };
}
```

#### Define the evaluator action

```ts
import { Genkit } from 'genkit';
import { BaseEvalDataPoint, EvaluatorAction } from 'genkit/evaluator';

/**
 * Configures a regex evaluator to match a US phone number.
 */
export function createUSPhoneRegexEvaluator(ai: Genkit): EvaluatorAction {
  return ai.defineEvaluator(
    {
      name: `myCustomEvals/usPhoneRegexEvaluator`,
      displayName: "Regex Match for US PHONE NUMBER",
      definition: "Uses Regex to check if output matches a US phone number",
      isBilled: false,
    },
    async (datapoint: BaseEvalDataPoint) => {
      const score = await usPhoneRegexScore(datapoint);
      return {
        testCaseId: datapoint.testCaseId,
        evaluation: score,
      };
    }
  );
}
```

## Putting it together

### Plugin definition

Plugins are registered with the framework by installing them at the time of
initializing  Genkit. To define a new plugin, use the `genkitPlugin` helper
method to instantiate all Genkit actions within the plugin context.

This code sample shows two evaluators: the LLM-based deliciousness evaluator,
and the regex-based US phone number evaluator. Instantiating these
evaluators within the plugin context registers them with the plugin.

```ts
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';

export function myCustomEvals<
  ModelCustomOptions extends z.ZodTypeAny
>(options: {
  judge: ModelArgument<ModelCustomOptions>;
  judgeConfig?: ModelCustomOptions;
}): GenkitPlugin {
  // Define the new plugin
  return genkitPlugin("myCustomEvals", async (ai: Genkit) => {
    const { judge, judgeConfig } = options;

    // The plugin instatiates our custom evaluators within the context
    // of the `ai` object, making them available
    // throughout our Genkit application.
    createDeliciousnessEvaluator(ai, judge, judgeConfig);
    createUSPhoneRegexEvaluator(ai);
  });
}
export default myCustomEvals;
```

### Configure Genkit

Add the `myCustomEvals` plugin to your Genkit configuration.

For evaluation with Gemini, disable safety settings so that the evaluator can
accept, detect, and score potentially harmful content.

```ts
import { gemini15Pro } from '@genkit-ai/googleai';

const ai = genkit({
  plugins: [
    vertexAI(),
    ...
    myCustomEvals({
      judge: gemini15Pro,
    }),
  ],
  ...
});
```

## Using your custom evaluators

Once you instantiate your custom evaluators within the Genkit app context
(either through a plugin or directly), they are ready to be used. The following
example illustrates how to try out the deliciousness evaluator with a few sample
inputs and outputs.

<ul style="list-style-type:none;">
  <li>1. Create a json file `deliciousness_dataset.json` with the following
  content:</li>
</ul>

```json
[
  {
    "testCaseId": "delicous_mango",
    "input": "What is a super delicious fruit",
    "output": "A perfectly ripe mango – sweet, juicy, and with a hint of tropical sunshine."
  },
  {
    "testCaseId": "disgusting_soggy_cereal",
    "input": "What is something that is tasty when fresh but less tasty after some time?",
    "output": "Stale, flavorless cereal that's been sitting in the box too long."
  }
]
```
<ul style="list-style-type:none;">
  <li>2. Use the Genkit CLI to run the evaluator against these test cases.</li>
  </ul>

```posix-terminal
# Start your genkit runtime
genkit start -- <command to start your app>

genkit eval:run deliciousness_dataset.json --evaluators=myCustomEvals/deliciousnessEvaluator
```
<ul style="list-style-type:none;">
  <li>3. Navigate to `localhost:4000/evaluate` to view your results in the
  Genkit UI.</li>
</ul>

It is important to note that confidence in custom evaluators increases as
you benchmark them with standard datasets or approaches. Iterate on the
results of such benchmarks to improve your evaluators' performance until it
reaches the targeted level of quality.
