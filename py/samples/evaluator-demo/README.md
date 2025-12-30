# Evaluation in Genkit

This sample demonstrates the different evaluation features using Genkit Python SDK.

Note: This sample focuses on evaluation features in Genkit, by utilizing the official Genkit Evaluators plugin. If you are interested in writing your own custom evaluator, please check the `custom/test_evaluator` defined in `src/main.py`.

## Setup and start the sample

```bash

# Start the Genkit Dev UI
genkit start -- uv run src/main.py
# This command should output the link to the Genkit Dev UI.
```
Choose any flow of interest and run in the Dev UI.
## Available Flows

- **setup**: Indexes the default PDF document (`docs/cat-handbook.pdf`) into the vector store
- **pdf_qa**: RAG flow that answers questions based on indexed PDF documents. It requires `setup` flow run first.
- **index_pdf**: Indexes a specified PDF file (defaults to `docs/cat-wiki.pdf`)
- **simple_structured**: Simple flow with structured input/output
- **simple_echo**: Simple echo flow
- **dog_facts_eval**: Programmatic evaluation flow using the faithfulness metric on a dog facts dataset

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

## Reference

For more details on using Genkit evaluations, please refer to the official [Genkit documentation](https://firebase.google.com/docs/genkit/evaluation).
