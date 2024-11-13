# Sample Vertex AI Plugin Reranker with Fake Document Content

This sample app demonstrates the use of the Vertex AI plugin for reranking a set of documents based on a query using fake document content. Follow this guide to set up and run the sample.

## Prerequisites

Before running this sample, ensure you have the following:

1. **Node.js** installed.
2. **PNPM** (Node Package Manager) installed.
3. A **Vertex AI** project with appropriate permissions for reranking models.
4. The **Discovery Engine API** enabled on your Google Cloud project. [Enable it here](https://console.cloud.google.com/apis/api/discoveryengine.googleapis.com/metrics).

## Getting Started

### Step 1: Clone the Repository and Install Dependencies

Clone this repository to your local machine and navigate to the project directory. Then, install the necessary dependencies:

\`\`\`bash
pnpm install
\`\`\`

### Step 2: Set Up Environment Variables

Create a \`.env\` file in the root directory and set the following variables. You can use the provided \`.env.example\` as a reference.

\`\`\`plaintext
PROJECT_ID=your_project_id_here
LOCATION=global
\`\`\`

These variables are required to configure the Vertex AI project and location for reranking.

### Step 3: Build the Project

Run the following command to build the project:

\`\`\`bash
pnpm build
\`\`\`

### Step 4: Run the Sample

To start the development environment and test the flow, run:

1. In the first terminal:

   \`\`\`bash
   pnpm genkit:dev
   \`\`\`

   This will start the Genkit development server.

2. In another terminal, use the UI or invoke the flow:

   \`\`\`bash
   genkit flow:run rerankFlow --input '{"query": "quantum mechanics"}'
   \`\`\`

   Alternatively, access the Genkit UI to interact with the flow.

## Sample Explanation

### Overview

This sample demonstrates how to use the Vertex AI plugin to rerank a predefined list of fake document content based on a query input. It leverages the \`semantic-ranker-512@latest\` model from Vertex AI.

### Key Components

- **Fake Document Content**: A hardcoded array of strings simulating document content.
- **Rerank Flow**: A flow that reranks the fake documents based on the provided query.
- **Genkit Configuration**: Configures Genkit with the Vertex AI plugin, setting up the project and reranking model.

### Rerank Flow

The \`rerankFlow\` function takes a query as input, reranks the predefined document content using the Vertex AI semantic reranker, and returns the documents sorted by relevance score.

\`\`\`typescript
export const rerankFlow = ai.defineFlow(
{
name: 'rerankFlow',
inputSchema: z.object({ query: z.string() }),
outputSchema: z.array(
z.object({
text: z.string(),
score: z.number(),
})
),
},
async ({ query }) => {
const documents = FAKE_DOCUMENT_CONTENT.map((text) =>
Document.fromText(text)
);
const reranker = 'vertexai/semantic-ranker-512@latest';

    const rerankedDocuments = await ai.rerank({
      reranker,
      query: Document.fromText(query),
      documents,
    });

    return rerankedDocuments.map((doc) => ({
      text: doc.text,
      score: doc.metadata.score,
    }));

}
);
\`\`\`

### Running the Server

The server is started using the \`startFlowServer\` function, which sets up the Genkit server to handle flow requests.

\`\`\`typescript
ai.startFlowServer({
flows: [rerankFlow],
});
\`\`\`

### Example Input and Output

- **Input**:

  \`\`\`json
  {
  "query": "quantum mechanics"
  }
  \`\`\`

- **Output**:

  \`\`\`json
  [
  { "text": "quantum mechanics", "score": 0.95 },
  { "text": "schrodinger's cat", "score": 0.85 },
  { "text": "e=mc^2", "score": 0.80 }
  ]
  \`\`\`

## License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.

## Conclusion

This sample provides a basic demonstration of using the Vertex AI plugin with Genkit for reranking documents based on a query. It can be extended and adapted to suit more complex use cases and integrations with other data sources and services.

For more information, refer to the official [Firebase Genkit documentation](https://firebase.google.com/docs/genkit).
