# Genkit RAG Sample

This sample demonstrates how to build RAG (Retrieval Augmented Generation) applications with Genkit Java using a local vector store for development.

## Features Demonstrated

- **Local Vector Store Plugin**: File-based vector storage for development and testing
- **Document Indexing**: Index documents from various sources
- **Semantic Retrieval**: Find relevant documents using embeddings
- **RAG Flows**: Combine retrieval with LLM generation
- **Multiple Knowledge Bases**: Separate vector stores for different domains

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Index Flow     │────▶│  Local Vec Store │◀────│  Retrieve Flow  │
│  (documents)    │     │  (embeddings)    │     │  (query)        │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  OpenAI LLM      │◀────│  RAG Flow       │
                        │  (generation)    │     │  (answer)       │
                        └──────────────────┘     └─────────────────┘
```

## Knowledge Bases

The sample includes three pre-configured knowledge bases:

1. **world-capitals**: Information about capital cities around the world
2. **dog-breeds**: Facts about popular dog breeds
3. **coffee-facts**: Information about coffee and brewing methods

## Prerequisites

- Java 17+
- Maven 3.6+
- OpenAI API key

## Running the Sample

### Option 1: Direct Run

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/rag

# Run the sample
./run.sh
# Or: mvn compile exec:java
```

### Option 2: With Genkit Dev UI (Recommended)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/rag

# Run with Genkit CLI
genkit start -- ./run.sh
```

The Dev UI will be available at http://localhost:4000

## Usage

### Step 1: Index the Data

Before querying, you need to index the documents:

```bash
# Index world capitals
curl -X POST http://localhost:8080/indexWorldCapitals

# Index dog breeds
curl -X POST http://localhost:8080/indexDogBreeds

# Index coffee facts
curl -X POST http://localhost:8080/indexCoffeeFacts
```

### Step 2: Query the Knowledge Bases

```bash
# Ask about world capitals
curl -X POST http://localhost:8080/askAboutCapitals \
  -H 'Content-Type: application/json' \
  -d '"What is the capital of France and what is it known for?"'

# Ask about dogs
curl -X POST http://localhost:8080/askAboutDogs \
  -H 'Content-Type: application/json' \
  -d '"What are good dog breeds for families with children?"'

# Ask about coffee
curl -X POST http://localhost:8080/askAboutCoffee \
  -H 'Content-Type: application/json' \
  -d '"How do you make espresso and what is a cappuccino?"'
```

### Step 3: Retrieve Documents Without Generation

```bash
# Just retrieve relevant documents
curl -X POST http://localhost:8080/retrieveDocuments \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "France capital",
    "store": "world-capitals",
    "k": 2
  }'
```

### Step 4: Index Custom Documents

```bash
curl -X POST http://localhost:8080/indexDocuments \
  -H 'Content-Type: application/json' \
  -d '[
    "The first fact about my topic.",
    "The second fact about my topic.",
    "The third fact about my topic."
  ]'
```

## How It Works

### Indexing

1. Documents are loaded from text files (one paragraph = one document)
2. Each document is converted to an embedding using OpenAI's embedding model
3. Documents and embeddings are stored in a JSON file on disk

### Retrieval

1. The query is converted to an embedding
2. Cosine similarity is computed between the query and all stored documents
3. The top-k most similar documents are returned

### Generation

1. Retrieved documents are formatted as context
2. The context and question are combined into a prompt
3. The LLM generates an answer based on the context

## Local Vector Store

The local vector store is designed for development and testing only. For production, use a proper vector database like:

- Pinecone
- Chroma
- Weaviate
- pgvector (PostgreSQL)
- Vertex AI Vector Search

### Storage Location

Documents are stored in JSON files at:
```
{java.io.tmpdir}/genkit-rag-sample/__db_{index-name}.json
```

## Adding Your Own Data

1. Create a text file with your content (paragraphs separated by blank lines)
2. Place it in `src/main/resources/data/`
3. Create a new `LocalVecConfig` for your data
4. Define indexing and query flows

## Development UI

Access the Genkit Development UI at http://localhost:3100 to:
- Browse available flows, indexers, and retrievers
- Test flows interactively
- View execution traces
- Inspect indexed documents

## Troubleshooting

### Empty Results
- Make sure you've indexed the documents first
- Check that the embedding model is working correctly

### Slow Indexing
- The first indexing takes longer due to embedding computation
- Subsequent runs use cached embeddings

### Out of Memory
- For large datasets, consider batch indexing
- Use a proper vector database for production
