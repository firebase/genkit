# Writing your own evaluators

This sample demonstrates how to write your own suite of custom evaluators. The evaluators in this package demonstrate how to write evaluators that leverage LLMs as well as a simple regex matcher. There are also simple test datasets to demonstrate how to use them.

## The Bring Your Own (BYO) custom evaluator plugin

To use a new evaluator, you need to define a custom evaluator plugin that is registered with genkit. We define this as a function `byoEval` in `src/index.ts`.

## Non LLM Evaluators

### Regex

Location: `src/regex`
Name: `byo/regex_match_{name}`
Output: numeric

The regex evaluator is an example that does not use an LLM. It also demonstrates how to create a factory method that can be parameterized.

## LLM Evaluators

### PII Detection

Location: `src/pii`
Name: `byo/pii_detection`
Output: boolean

An evaluator that attempts to detect PII in your output.

### Funniness

Location: `src/funniness`
Name: `byo/funniness`
Output: enum/categorization (FUNNY_JOKE, NOT_FUNNY_JOKE, OFFENSIVE_JOKE, NOT_A_JOKE)

An evaluator that attempts to judge if a passed statement is a joke and if it is funny.

### Deliciousness

Location: `src/deliciousness`
Name: `byo/deliciousness`
Output: string (yes, no, maybe)

An evaluator that attempts to judge if a passed statement is delicious literally or metaphorically.

## Build and start the app

```posix-terminal
pnpm build
```

or if you need to, build everything:

```posix-terminal
cd ../../../; pnpm build; pnpm pack:all; cd -
```

Start the testapp

```posix-terminal
genkit start -- pnpm dev
```

## Test your evaluator

Note: Run these commands in a separate terminal.

Regex:

```posix-terminal
genkit eval:run datasets/regex_dataset.json --evaluators=byo/regex_match_url,byo/regex_match_us_phone
```

PII Detection:

```posix-terminal
genkit eval:run ./datasets/pii_detection_dataset.json --evaluators=byo/pii_detection
```

Funniness:

```posix-terminal
genkit eval:run datasets/funniness_dataset.json --evaluators=byo/funniness
```

Deliciousness:

```posix-terminal
genkit eval:run datasets/deliciousness_dataset.json --evaluators=byo/deliciousness
```

Note: The evaluators implemented in this plugin do not consider the `input` provided to the model as part of the evaluation. Therefore, many of the test datasets provided in this testapp have `input` set to `"input"`. If you are implementing an evaluator that utilizes the input provied to the model, you have to provide the actual input in this field.

## See your results

Navigate to the `Evaluations` section in the Dev UI.
