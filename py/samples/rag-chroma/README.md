# RAG with ChromaDB Demo - Cat Knowledge Base 🐱

A complete Retrieval-Augmented Generation (RAG) demo using ChromaDB as an
in-memory vector store with Genkit. Features a cat-themed knowledge base!

## Overview

This sample demonstrates the RAG pattern:

1. **Index Phase**: Cat knowledge documents are embedded and stored in ChromaDB
2. **Retrieval Phase**: User questions find relevant documents via similarity search
3. **Generation Phase**: Retrieved context augments the LLM's response

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAG Architecture                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INDEX PHASE:                                                                │
│  ┌─────────────────┐    ┌──────────┐    ┌─────────────┐    ┌───────────┐   │
│  │  Cat Documents  │ ─► │ Embedder │ ─► │ Embeddings  │ ─► │ ChromaDB  │   │
│  │  (txt, json)    │    │ (Gemini) │    │ (Vectors)   │    │(In-Memory)│   │
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

## Quick Start

### 1. Set Up API Key

```bash
export GOOGLE_API_KEY=your-api-key
```

Get a key from: [Google AI Studio](https://makersuite.google.com/app/apikey)

### 2. Run the Demo

```bash
./run.sh
```

This will:
- Install all dependencies (including ChromaDB)
- Start the Genkit Dev UI at http://localhost:4000
- **Automatically index the cat knowledge base!**
- Watch for file changes and auto-reload

### 3. Use the Demo

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
| `index_cat_knowledge_flow` | Load and index all cat documents into ChromaDB |
| `ask_about_cats_flow` | Ask questions with RAG-powered answers |
| `list_sample_questions_flow` | Get example questions to try |

## Architecture Details

### Why ChromaDB?

- **Zero Setup**: Runs in-memory, no external services needed
- **Fast**: Efficient similarity search for retrieval
- **Flexible**: Supports metadata filtering and various distance metrics
- **Open Source**: Free to use with a large community

### Embedding Model

Uses `googleai/text-embedding-004` for:
- Document embedding during indexing
- Query embedding during retrieval

### Generation Model

Uses `googleai/gemini-2.0-flash` for:
- Generating answers based on retrieved context
- Fast, accurate responses

## Troubleshooting

### "GOOGLE_API_KEY not set"

```bash
export GOOGLE_API_KEY=your-api-key
```

### "No documents found"

Make sure the data files exist in `./data/`:
```bash
ls -la data/
```

### "I don't have information about that"

Run `index_cat_knowledge_flow` first to load the knowledge base.

## Learn More

- [Genkit Documentation](https://genkit.dev/docs)
- [ChromaDB Documentation](https://www.trychroma.com/)
- [RAG Pattern](https://genkit.dev/docs/rag)

## License

Apache 2.0
