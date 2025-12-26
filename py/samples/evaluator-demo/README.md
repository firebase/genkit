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
## Available Flows

- **setup**: Indexes the default PDF document (`docs/cat-handbook.pdf`) into the vector store
- **index_pdf**: Indexes a specified PDF file (defaults to `docs/cat-wiki.pdf`)
- **pdf_qa**: RAG flow that answers questions based on indexed PDF documents. It requires `setup` flow run first.
- **simple_structured**: Simple flow with structured input/output
- **simple_echo**: Simple echo flow
- **dog_facts_eval**: Programmatic evaluation flow using the faithfulness metric on a dog facts dataset

## Reference

For more details on using Genkit evaluations, please refer to the official [Genkit documentation](https://firebase.google.com/docs/genkit/evaluation).
