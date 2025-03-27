# Evaluation in Genkit

This testapp demonstrates the different evaluation features using Genkit.

Note: This testapp focuses on evaluation features in Genkit, by utilizing the official Genkit Evals plugin or other third-party plugin. If you are interested in writing your own custom evaluator, please check out the `custom-evaluators` testapp.

## Setup and start the testapp

```posix-terminal
# Build the app
pnpm build

# Use this command if you need to build everything
# cd ../../../; pnpm build; pnpm pack:all; cd -

# Start the app

genkit start -- pnpm dev
# This command should output the link to the Genkit Dev UI.
```

The rest of the commands in this guide must be run in a separate terminal.

```posix-terminal
# Index "docs/cat-handbook.pdf" to start
# testing Genkit evaluation features. Please see
# src/setup.ts for more details.

genkit flow:run setup
```

## Evaluations

### Simple inference and evaluation

Use the `eval:flow` command to run a flow against a set of input samples and
evaluate the generated outputs.

```posix-terminal
genkit eval:flow pdfQA --input data/cat_adoption_questions.json --evaluator=genkitEval/maliciousness
```

Once this commands succeeds, you can navigate to the `Evaluations` section in the Dev UI to view your evaluation results.

You can try other combinations of inputs and evaluators to see how they work. Omitting the `evaluator` flag will trigger evaluation against **all** Genkit evaluators installed in the app.

### Evaluation in code

Please see the `src/eval-in-code.ts` file for an example on running evaluations from within code.

## Reference

For more details on using Genkit evaluations, please refer to the official [Genkit documentation](https://firebase.google.com/docs/genkit/evaluation).
