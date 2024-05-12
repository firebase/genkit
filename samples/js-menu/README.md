## Menu Understanding Sample Application

This sample demonstrates an application that can understand a restaurant menu and answer relevant questions about the items on the menu.

There are 5 iterations of this sample application, growing in complexity and demonstrating utilization of many different Genkit features.

To test each one out, open the Developer UI and exercise the prompts and flows. Each step contains one or more `example.json` files which you can use as inputs.

### Prerequisites

This example uses Vertex AI for language models and embeddings.

### Prompts and Flows

1. This step shows how to define prompts in code that can accept user input to their templates.
2. This step illustrates how to wrap your llm calls and other application code into flows with strong input and output schemas.
   It also adds an example of tool usage to load the menu from a data file.
3. This step adds session history and supports a multi-turn chat with the model.
4. This step ingests the menu items into a vector database and uses retrieval to include releveant menu items in the prompt.
5. This step illustrates how to combine models with different modalities. It uses a vision model to ingest the menu items from a photograph.

## Running the sample

```bash
npm i
genkit start
```
