# Evaluation in Genkit

This sample demonstrates the different evaluation features using Genkit Python SDK.

Note: This sample focuses on evaluation features in Genkit, by utilizing the official Genkit Evaluators plugin. If you are interested in writing your own custom evaluator, please check the `custom/test_evaluator` defined in `src/index.py`.

## Setup and start the sample

```bash

# Start the Genkit Dev UI
genkit start -- uv run samples/evaluator-demo/src/index.py
# This command should output the link to the Genkit Dev UI.
```

The rest of the commands in this guide can be run in a separate terminal or directly in the Dev UI.

### Initial Setup

```bash
# Index "docs/cat-handbook.pdf" to start
# testing Genkit evaluation features. Please see
# src/setup.py for more details.

genkit flow:run setup
```

## Evaluations

### Running Evaluations via CLI

Use the `eval:flow` command to run a flow against a dataset and evaluate the outputs:

```bash
# Evaluate with a specific evaluator
genkit eval:flow pdf_qa --input data/cat_adoption_questions.json --evaluator=custom/test_evaluator

# Evaluate with multiple evaluators
genkit eval:flow pdf_qa --input data/cat_adoption_questions.json --evaluator=genkitEval/faithfulness --evaluator=genkitEval/maliciousness

# Evaluate with all available evaluators (omit --evaluator flag)
genkit eval:flow pdf_qa --input data/cat_adoption_questions.json
```

### Running Evaluations in Dev UI

1. Navigate to the **Evaluations** tab in the Dev UI
2. Click **"Run Evaluation"** or **"New Evaluation"**
3. Configure:
   - **Flow**: Select the flow to evaluate (e.g., `pdf_qa`)
   - **Dataset**: Upload or select a JSON file (e.g., `data/cat_adoption_questions.json`)
   - **Evaluators**: Select one or more evaluators:
     - `custom/test_evaluator` - Random evaluator for testing (fast, no LLM calls)
     - `genkitEval/faithfulness` - Checks if output is faithful to context
     - `genkitEval/maliciousness` - Detects harmful content
     - `genkitEval/answer_relevancy` - Checks if answer is relevant to question
4. Click **"Run"**
5. View results in the Evaluations tab

### Programmatic Evaluation

The `dog_facts_eval` flow demonstrates running evaluations from code. See `src/eval_in_code.py` for implementation details.

```bash
# Run programmatic evaluation
genkit flow:run dog_facts_eval
```

**Note:** The `dog_facts_eval` flow evaluates 20 test cases with the faithfulness metric, making 40 LLM API calls. This takes approximately 5 minutes to complete.

## Available Flows

- **setup**: Indexes the default PDF document (`docs/cat-handbook.pdf`) into the vector store
- **index_pdf**: Indexes a specified PDF file (defaults to `docs/cat-wiki.pdf`)
- **pdf_qa**: RAG flow that answers questions based on indexed PDF documents. It requires `setup` flow run first.
- **simple_structured**: Simple flow with structured input/output
- **simple_echo**: Simple echo flow
- **dog_facts_eval**: Programmatic evaluation flow using the faithfulness metric on a dog facts dataset

## Reference

For more details on using Genkit evaluations, please refer to the official [Genkit documentation](https://firebase.google.com/docs/genkit/evaluation).
