# RAG with Pinecone Demo - Cat Knowledge Base 🐱

A complete Retrieval-Augmented Generation (RAG) demo using Pinecone as a
managed vector database with Genkit. Features a cat-themed knowledge base!

## Overview

This sample demonstrates the RAG pattern with Pinecone:

1. **Index Phase**: Cat knowledge documents are embedded and stored in Pinecone
2. **Retrieval Phase**: User questions find relevant documents via similarity search
3. **Generation Phase**: Retrieved context augments the LLM's response

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAG Architecture                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INDEX PHASE:                                                                │
│  ┌─────────────────┐    ┌──────────┐    ┌─────────────┐    ┌───────────┐   │
│  │  Cat Documents  │ ─► │ Embedder │ ─► │ Embeddings  │ ─► │ Pinecone  │   │
│  │  (txt, json)    │    │ (Gemini) │    │ (Vectors)   │    │ (Cloud)   │   │
│  └─────────────────┘    └──────────┘    └─────────────┘    └───────────┘   │
│                                                                              │
│  QUERY PHASE:                                                                │
│  ┌──────────┐    ┌──────────┐    ┌────────────┐    ┌──────────────────┐    │
│  │ Question │ ─► │ Embedder │ ─► │ Similarity │ ─► │ Retrieved Docs   │    │
│  └──────────┘    └──────────┘    │   Search   │    └────────┬─────────┘    │
│                                  └────────────┘             │               │
│                                                             │               │
│  GENERATION PHASE:                                          ▼               │
│  ┌───────────┐                  ┌─────────────────────────────────────┐    │
│  │  Answer   │ ◄───────────────│ LLM (Gemini) + Context from Docs   │    │
│  └───────────┘                  └─────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. Create a Pinecone Account

Sign up at [Pinecone](https://www.pinecone.io/) (free tier available).

### 2. Create a Pinecone Index

```bash
./run.sh --setup
```

This will show detailed instructions. In short:
1. Go to https://app.pinecone.io/
2. Create a new index:
   - **Name**: `cat-knowledge`
   - **Dimensions**: `768`
   - **Metric**: `cosine`

### 3. Set API Keys

```bash
export PINECONE_API_KEY=your-pinecone-key
export GOOGLE_API_KEY=your-google-key
```

## Quick Start

### Run the Demo

```bash
./run.sh
```

This will:
- Install all dependencies (including Pinecone client)
- Start the Genkit Dev UI at http://localhost:4000
- **Automatically index the cat knowledge base!**
- Watch for file changes and auto-reload

### Use the Demo

1. Open http://localhost:4000 in your browser

2. **Ask questions about cats** (knowledge base is pre-indexed):
   - Select `ask_about_cats_flow`
   - Enter questions like:
     - "Why do cats purr?"
     - "Tell me about Grumpy Cat"
     - "What vaccinations do cats need?"
   - The answer will include sources from the knowledge base

3. **Get question ideas**:
   - Run `list_sample_questions_flow` for example questions

4. **Re-index if needed** (after adding new data):
   - Run `index_cat_knowledge_flow` to refresh the knowledge base

## Data Files

The knowledge base includes three cat-themed sources in `./data/`:

| File | Description |
|------|-------------|
| `cat_care_guide.txt` | Comprehensive guide on cat behavior, nutrition, health, and breeds |
| `famous_cats.txt` | Stories of famous cats from internet celebrities to historical cats |
| `cat_facts.json` | Fun and interesting facts about cats organized by category |

### Adding Your Own Data

You can add more documents by:
1. Adding `.txt` files to `./data/` (will be split by `##` headers)
2. Adding facts to `cat_facts.json`
3. Running `index_cat_knowledge_flow` again

## Flows

| Flow | Description |
|------|-------------|
| `index_cat_knowledge_flow` | Load and index all cat documents into Pinecone |
| `ask_about_cats_flow` | Ask questions with RAG-powered answers |
| `list_sample_questions_flow` | Get example questions to try |

## Namespaces

Pinecone supports namespaces for data isolation. You can use different namespaces
to organize data:

```python
# Index to a specific namespace
await ai.index(
    indexer=pinecone_indexer_ref(index_id='cat-knowledge'),
    documents=documents,
    options={'namespace': 'production'},
)

# Query from a specific namespace
results = await ai.retrieve(
    retriever=pinecone_retriever_ref(index_id='cat-knowledge'),
    query='Why do cats purr?',
    options={'namespace': 'production', 'k': 5},
)
```

## Why Pinecone?

- **Managed Service**: No infrastructure to maintain
- **Scalable**: Handles billions of vectors
- **Fast**: Low-latency similarity search
- **Filtering**: Metadata filtering for precise results
- **Multi-tenancy**: Namespaces for data isolation

## Architecture Details

### Embedding Model

Uses `googleai/text-embedding-004` for:
- Document embedding during indexing (768 dimensions)
- Query embedding during retrieval

### Generation Model

Uses `googleai/gemini-2.0-flash` for:
- Generating answers based on retrieved context
- Fast, accurate responses

## Troubleshooting

### "PINECONE_API_KEY not set"

```bash
export PINECONE_API_KEY=your-pinecone-key
```

### "Index not found" or connection errors

1. Verify your index exists at https://app.pinecone.io/
2. Check the index name matches `INDEX_ID` in `src/main.py`
3. Ensure the index has dimension=768 and metric=cosine

### "GOOGLE_API_KEY not set"

```bash
export GOOGLE_API_KEY=your-google-key
```

### "No documents found"

Make sure the data files exist in `./data/`:
```bash
ls -la data/
```

### "I don't have information about that"

Run `index_cat_knowledge_flow` first to load the knowledge base.

## Cost Considerations

- Pinecone free tier includes 1 index with ~100K vectors
- Google AI API has generous free quotas for testing
- This demo uses ~50 documents, well within free tier limits

## Learn More

- [Genkit Documentation](https://genkit.dev/docs)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [RAG Pattern](https://genkit.dev/docs/rag)

## License

Apache 2.0
