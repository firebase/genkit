# Cloud SQL for PostgreSQL plugin

The Cloud SQL for PostgreSQL plugin provides indexer and retriever implementations that use PostgreSQL with the pgvector extension for vector similarity search.

## Installation

```posix-terminal
npm i --save @genkitx-cloud-sql-pg
```

## Configuration

To use this plugin, first create a `PostgresEngine` instance:

```ts
import { PostgresEngine } from '@genkit-ai/cloud-sql-pg';

// Create PostgresEngine instance
const engine = await PostgresEngine.fromInstance('my-project', 'us-central1', 'my-instance', 'my-database');

// Create the vector store table
await engine.initVectorstoreTable('my-documents', 768);

// Or create a custom vector store table
await engine.initVectorstoreTable('my-documents', 768, {
  schemaName: 'public',
  contentColumn: 'content',
  embeddingColumn: 'embedding',
  idColumn: 'custom_id', // Custom ID column name
  metadataColumns: [
    { name: 'source', dataType: 'TEXT' },
    { name: 'category', dataType: 'TEXT' }
  ],
  metadataJsonColumn: 'metadata',
  storeMetadata: true,
  overwriteExisting: true
});
```

Then, specify the plugin when you initialize Genkit:

```ts
import { genkit } from 'genkit';
import { postgres } from '@genkit-ai/cloud-sql-pg';
import { textEmbedding004 } from '@genkit-ai/vertexai';

const ai = genkit({
  plugins: [
    postgres([
      {
        tableName: 'my-documents',
        engine: engine,
        embedder: textEmbedding004,
        // Use additional fields to connect to a custom vector store table
        // schemaName: 'public', 
        // contentColumn: 'custom_content',
        // embeddingColumn: 'custom_embedding',
        // idColumn: 'custom_id', // Match the ID column from table creation
        // metadataColumns: ['source', 'category'],
        // metadataJsonColumn: 'my_json_metadata',
      },
    ]),
  ],
});

// To use the table you configured when you loaded the plugin:
await ai.index({ 
  indexer: postgresIndexerRef, 
  documents: [
    {
      content: [{ text: "The product features include..." }],
      metadata: {
        source: "website",
        category: "product-docs",
        custom_id: "doc-123" // This will be used as the document ID
      }
    }
  ]
});

// To retrieve from the configured table:
const query = "What are the key features of the product?";
let docs = await ai.retrieve({ 
  retriever: postgresRetrieverRef, 
  query,
  options: {
    k: 5,
    filter: {
      category: 'product-docs',
      source: 'website'
    }
  }
});
```

## Usage

Import retriever and indexer references like so:

```ts
import { postgresRetrieverRef, postgresIndexerRef } from '@genkit-ai/cloud-sql-pg';
```

### Index Documents

You can create reusable references for your indexers:

```ts
export const myDocumentsIndexer = postgresIndexerRef({
  tableName: 'my-custom-documents',
  idColumn: 'custom_id',
  metadataColumns: ['source', 'category']
});
```

Then use them to index documents:

```ts
// Index with custom ID from metadata
const docWithCustomId = new Document({
  content: [{ text: 'Document with custom ID' }],
  metadata: { 
    source: 'test',
    category: 'docs',
    custom_id: 'custom-123'
  }
});

await ai.index({
  indexer: myDocumentsIndexer,
  documents: [docWithCustomId]
});

// Index with custom batch size
await ai.index({ 
  indexer: myDocumentsIndexer, 
  documents: [
    {
      content: [{ text: "The product features include..." }],
      metadata: {
        source: "website",
        category: "product-docs",
        custom_id: "doc-456"
      }
    }
  ],
  options: { batchSize: 10 }
});
```

### Retrieve Documents

Create reusable references for your retrievers:

```ts
export const myDocumentsRetriever = postgresRetrieverRef({
  tableName: 'my-documents',
  idColumn: 'custom_id',
  metadataColumns: ['source', 'category']
});
```

Then use them to retrieve documents:

```ts
const query = "What are the key features of the product?";
let docs = await ai.retrieve({ 
  retriever: myDocumentsRetriever, 
  query,
  options: {
    k: 5, // Number of documents to return
    filter: "source = 'website'" // Optional filter on metadata columns
  }
});
```

See the [Retrieval-augmented generation](../rag.md) page for a general discussion on indexers and retrievers. 
