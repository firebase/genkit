# Glossary

This glossary provides definitions for terms used throughout Genkit.
ELI5 explanations are provided where helpful.

## Genkit Core Concepts

| **Term**                 | Definition | ELI5 |
|--------------------------|------------|------|
| **Action**               | A named, typed, observable function that can be called locally or via HTTP. The fundamental building block of Genkit. | A "button" that does one thing. Press it, something happens. |
| **Flow**                 | A user-defined action. Your custom logic wrapped in Genkit's action system. | YOUR button that does YOUR thing. |
| **Registry**             | The central in-memory storage where all actions are registered and looked up by name. | A phone book for actions. Need a model? Look it up. |
| **Plugin**               | An extension that adds new capabilities by registering actions (models, embedders, tools). | An "app" you install to add new features. |
| **Veneer**               | The user-friendly API layer (Genkit class) that simplifies interaction with the framework. | The nice buttons on the remote, not the circuit board inside. |
| **Blocks**               | Higher-level AI abstractions (models, embedders, retrievers) built on top of actions. | Lego pieces you snap together to build AI apps. |
| **Middleware**           | Functions that wrap action calls to add cross-cutting behavior (retry, logging, etc.). | A secretary who handles calls for you (retries, fallbacks). |

## AI/ML Concepts

| **Term**                                 | Definition | ELI5 |
|------------------------------------------|------------|------|
| **Model**                                | An AI system that generates content (text, images, etc.) given a prompt. Examples: Gemini, Claude, GPT. | An AI brain that writes/draws for you. |
| **Embedding**                            | A numerical vector representation of text that captures its semantic meaning. | Converting words into numbers that capture meaning. |
| **Embedder**                             | An action that converts text into embeddings. | A translator that turns words into math. |
| **Tool**                                 | A function that an AI model can call to perform actions or retrieve information. | A helper the AI can ask to do things. |
| **Prompt**                               | Instructions given to a model to guide its output. | The question or task you give the AI. |
| **Prompt Template**                      | A reusable prompt with variable placeholders, often stored in `.prompt` files. | A fill-in-the-blank prompt template. |

## RAG (Retrieval Augmented Generation)

| **Term**                                 | Definition | ELI5 |
|------------------------------------------|------------|------|
| **Retrieval Augmented Generation (RAG)** | A technique that combines LLMs with external knowledge sources to generate more accurate responses. | Giving the AI a reference book to look things up. |
| **Retriever**                            | An action that fetches relevant documents from a data source based on a query. | A librarian who finds books matching your question. |
| **Reranker (Cross-encoder)**             | A model that takes a query and document pair and outputs a relevance score, used to reorder search results. | A second opinion on which books are most relevant. |
| **Vector Store**                         | A database optimized for storing and searching embeddings using similarity algorithms. | A special bookshelf organized by meaning, not alphabetically. |
| **Bi-encoder**                           | A model that compresses text meaning into a single vector. Used for fast initial retrieval. | A quick summary machine for finding candidates fast. |
| **Two-Stage Retrieval**                  | First retrieve many documents quickly (bi-encoder), then rerank them accurately (cross-encoder). | Get 100 candidates fast, then carefully pick the best 5. |
| **Context Stuffing**                     | Overloading the context window with too much information, degrading LLM performance. | Giving someone so many books they can't focus on any. |
| **Context Window**                       | The maximum amount of text an LLM can process at once. | The size of the AI's "working memory". |
| **Semantic Search**                      | Searching by meaning rather than exact keyword matches. | Finding "car" when you search for "automobile". |
| **Vector Search**                        | Finding similar items by comparing their embedding vectors. | Finding books "close" to yours in the meaning-organized library. |

## Evaluation & Metrics

| **Term**                 | Definition | ELI5 |
|--------------------------|------------|------|
| **Evaluator**            | An action that scores model outputs based on specific criteria. | A grader who checks the AI's homework. |
| **BLEU Score**           | A metric comparing generated text to reference text (translation quality). | How close is your answer to the "correct" answer? |
| **ROUGE Score**          | A metric measuring how much key information is captured (summarization quality). | Did you hit all the important points? |
| **Fluency**              | A metric assessing how natural and readable generated text is. | Does it sound like a human wrote it? |
| **Groundedness**         | A metric checking if output is supported by provided context (no hallucinations). | Did the AI make things up or stick to the facts? |
| **Recall**               | The proportion of relevant documents that were retrieved. | Of all the good books, how many did we find? |
| **LLM Recall**           | The ability of an LLM to find specific information within its context window. | Can the AI find the needle in the haystack you gave it? |

## Tool Calling & Agents

| **Term**                 | Definition | ELI5 |
|--------------------------|------------|------|
| **Tool Calling**         | The ability for a model to request execution of defined tools during generation. | The AI asking helpers to do things for it. |
| **Tool Interrupt**       | Pausing tool execution to get user confirmation before proceeding. | "Are you sure you want to book this flight?" |
| **Agent**                | An AI system that uses tools (including other agents) to accomplish complex tasks autonomously. | An AI that can do multi-step tasks on its own. |
| **Agentic Loop**         | The cycle where an agent generates, calls tools, observes results, and continues until done. | Think → Act → Observe → Repeat until done. |

## Observability

| **Term**                 | Definition | ELI5 |
|--------------------------|------------|------|
| **Span**                 | A named, timed operation in a trace (e.g., a single action call). | A stopwatch for one task. |
| **Trace**                | A collection of spans showing a request's journey through the system. | Breadcrumbs showing the path through your code. |
| **OpenTelemetry**        | An open standard for observability (tracing, metrics, logs) used by Genkit. | A universal language for tracking what your code does. |

## Status Codes

Genkit uses gRPC-style status codes for error handling:

| **Status**            | HTTP | When Used |
|-----------------------|------|-----------|
| `OK`                  | 200  | Success |
| `INVALID_ARGUMENT`    | 400  | Bad request parameters |
| `UNAUTHENTICATED`     | 401  | Missing or invalid credentials |
| `PERMISSION_DENIED`   | 403  | Not allowed to do this |
| `NOT_FOUND`           | 404  | Resource doesn't exist |
| `RESOURCE_EXHAUSTED`  | 429  | Rate limited |
| `CANCELLED`           | 499  | Client cancelled request |
| `INTERNAL`            | 500  | Server error |
| `UNAVAILABLE`         | 503  | Service temporarily down |
| `DEADLINE_EXCEEDED`   | 504  | Request timed out |
