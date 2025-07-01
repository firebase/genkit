# MongoDB Plugin Test Application

This test application demonstrates the comprehensive capabilities of the MongoDB plugin for Genkit, showcasing vector search, text search, hybrid search, CRUD operations, search index management, and multimodal document processing.

## Features Demonstrated

- **Vector Search**: Semantic search using embeddings with MongoDB's vector search capabilities
- **Text Search**: Full-text search with fuzzy matching and synonyms support
- **Hybrid Search**: Combine vector and text search for enhanced results
- **CRUD Operations**: Create, read, update, and delete documents by ID
- **Search Index Management**: Create, list, and drop search indexes
- **Multimodal Processing**: Image indexing and retrieval using multimodal embeddings
- **Document Processing**: PDF document processing with text extraction and image extraction
- **Menu Understanding**: Restaurant menu analysis with both vector and text search
- **Batch Indexing**: Efficient document indexing with configurable batch sizes
- **Flexible Field Configuration**: Customizable field names for data, metadata, and embeddings

## Prerequisites

- **Node.js** (version 18 or higher)
- **MongoDB** (6.0+ with Atlas Search or local search indexes)
- **Google Cloud Project** with Vertex AI enabled
- **Google AI API** access for embeddings

## Environment Setup

Create a `.env` file in the root directory with the following variables:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=your_database_name
MONGODB_COLLECTION_NAME=your_collection_name
MONGODB_MEDIA_COLLECTION_NAME=your_media_collection
MONGODB_IMAGE_COLLECTION_NAME=your_image_collection
MONGODB_DOCUMENT_COLLECTION_NAME=your_document_collection

# Google Cloud Configuration
PROJECT_ID=your_google_cloud_project_id
LOCATION=us-central1
```

## Installation

```bash
pnpm install
```

## Running the Application

### Development Mode

```bash
pnpm run dev
```

### Start with Genkit UI

```bash
pnpm run start
```

This will start the Genkit UI where you can interact with all the flows and prompts.

## Application Structure

### Core Features

#### 1. Menu Understanding (`src/core/menu/`)

Demonstrates restaurant menu analysis with multiple search strategies:

- **Menu Indexer Flow**: Indexes menu items with embeddings for semantic search
- **Vector Search Flow**: Finds relevant menu items using semantic similarity
- **Text Search Flow**: Performs full-text search with fuzzy matching

**Example Usage:**
```typescript
// Index menu items
await ai.runFlow('Menu - Indexer Flow', menuItems);

// Search by semantic similarity
await ai.runFlow('Menu - Retrieve Vector Flow', { question: "What vegetarian options do you have?" });

// Search by text matching
await ai.runFlow('Menu - Retrieve Text Flow', { question: "Show me items with chicken" });
```

**Key Features:**
- Custom field names for menu data (`menuItem`, `menuItemType`, `menuItemMetadata`)
- Configurable batch size for efficient indexing
- Support for both vector and text search strategies

#### 2. Image Processing (`src/core/image/`)

Demonstrates multimodal document processing with image embeddings:

- **Image Indexer Flow**: Indexes images with multimodal embeddings using Vertex AI's multimodalEmbedding001
- **Image Retriever Flow**: Finds similar images using vector search with cosine similarity

**Example Usage:**
```typescript
// Index an image with description
await ai.runFlow('Image - Indexer Flow', {
  name: 'cat',
  description: 'A fluffy orange cat sitting on a windowsill'
});

// Find similar images by providing an image name
await ai.runFlow('Image - Retrieve Flow', { name: 'cat' });
```

**Key Features:**
- Uses multimodal embeddings for image understanding
- Supports image similarity search
- Custom field names for image data (`imageData`, `imageType`, `imageMetadata`)
- Optional data storage with `skipData` option

#### 3. Document Processing (`src/core/document/`)

Demonstrates PDF document processing with text and image extraction:

- **Document Indexer Flow**: Processes PDF documents with text chunking and image extraction
- **Document Retriever Flow**: Retrieves relevant document chunks using vector search

**Example Usage:**
```typescript
// Index a PDF document
await ai.runFlow('Document - Indexer Flow', {
  name: 'sample-document'
});

// Query document content
await ai.runFlow('Document - Retrieve Flow', { question: "What is the main topic?" });
```

**Key Features:**
- PDF text extraction and chunking with configurable parameters
- Image extraction from PDF documents
- Multimodal embeddings for both text and image content
- Custom field names for document data (`documentType`, `documentMetadata`)

### Tool Management

#### 4. CRUD Operations (`src/crud/`)

Demonstrates basic database operations by document ID:

- **CRUD Management Flow**: Handles create, read, update, and delete operations

**Available Tools:**
- `mongodb/crud/create` - Create new documents
- `mongodb/crud/read` - Read documents by ID
- `mongodb/crud/update` - Update documents by ID
- `mongodb/crud/delete` - Delete documents by ID

**Example Usage:**
```typescript
// Create a new menu item
await ai.runFlow('CRUD Management Flow', {
  request: "Create a new menu item: Margherita Pizza - Fresh mozzarella, tomato sauce, basil - $18.99"
});

// Read a menu item by ID
await ai.runFlow('CRUD Management Flow', {
  request: "Read menu item with ID: 507f1f77bcf86cd799439011"
});
```

#### 5. Search Index Management (`src/search-index/`)

Demonstrates search index administration:

- **Search Index Management Flow**: Manages search indexes

**Available Tools:**
- `mongodb/search-index/create` - Create new search indexes
- `mongodb/search-index/list` - List existing indexes
- `mongodb/search-index/drop` - Drop search indexes

**Example Usage:**
```typescript
// Create a text search index
await ai.runFlow('Search Index Management Flow', {
  request: "Create a text search index named 'text_index' for the 'data' field"
});

// List all search indexes
await ai.runFlow('Search Index Management Flow', {
  request: "List all search indexes in the collection"
});
```

## Configuration

### MongoDB Plugin Setup

The application configures the MongoDB plugin with:

```typescript
mongodb([
  {
    url: MONGODB_URL,
    indexer: {
      id: 'indexer',
      retry: {
        retryAttempts: 3,
        baseDelay: 1000,
        jitterFactor: 0.1,
      },
    },
    retriever: {
      id: 'retriever',
      retry: {
        retryAttempts: 2,
        baseDelay: 500,
      },
    },
    crudTools: { id: 'crudTools' },
    searchIndexTools: { id: 'searchIndexTools' },
  },
])
```

### AI Models Used

- **Google AI**: `gemini-2.5-flash` for text generation
- **Google AI**: `text-embedding-004` for text embeddings
- **Vertex AI**: `multimodalEmbedding001` for image and document embeddings

## Example Workflows

### 1. Menu Analysis Workflow

1. **Index Menu Items**: Use the Menu Indexer Flow to add menu items to the database
2. **Semantic Search**: Use Vector Search Flow to find items based on meaning
3. **Text Search**: Use Text Search Flow for exact text matching with fuzzy search

### 2. Image Search Workflow

1. **Index Images**: Use Image Indexer Flow to add images with descriptions and generate multimodal embeddings
2. **Find Similar Images**: Use Image Retriever Flow to find visually similar images using vector search
3. **Image Processing**: Demonstrates multimodal embeddings for image similarity search with configurable field names
4. **Metadata Management**: Store and retrieve image metadata for enhanced search capabilities

### 3. Document Processing Workflow

1. **Index Documents**: Use Document Indexer Flow to process PDF documents with text chunking and image extraction
2. **Query Documents**: Use Document Retriever Flow to find relevant document chunks using vector search
3. **Multimodal Processing**: Demonstrates handling of both text and image content from documents
4. **Chunking Strategy**: Configurable text chunking with overlap and length parameters

### 4. Database Management Workflow

1. **Create Documents**: Use CRUD tools to add new documents
2. **Query Documents**: Use CRUD tools to retrieve documents by ID
3. **Update Documents**: Use CRUD tools to modify existing documents
4. **Delete Documents**: Use CRUD tools to remove documents

### 5. Search Index Workflow

1. **Create Indexes**: Use search index tools to create text and vector search indexes
2. **List Indexes**: Use search index tools to view existing indexes
3. **Manage Indexes**: Use search index tools to drop indexes when needed

## Testing

### Using Example Data

Each flow includes example JSON files that you can use as inputs in the Genkit UI:

- `src/core/menu/examples/` - Sample menu items
- `src/core/image/examples/` - Sample image data
- `src/core/document/examples/` - Sample document processing requests
- `src/crud/examples/` - Sample CRUD operations
- `src/search-index/examples/` - Sample index configurations

### Interactive Testing

1. Start the application with `pnpm run start`
2. Open the Genkit UI in your browser
3. Navigate to the Flows section
4. Select any flow and use the example data or provide your own inputs
5. View the results and examine the MongoDB collections

## Database Schema

### Menu Collection
```typescript
{
  embedding: number[],       // Vector embedding
  menuItem: string,          // Menu item text
  menuItemType: string,      // Document type
  menuItemMetadata: MenuItem, // Menu item metadata
  createdAt: Date            // Indexing timestamp
}
```

### Image Collection
```typescript
{
  embedding: number[],       // Multimodal embedding
  imageType: string,         // Document type
  imageMetadata: object,     // Image metadata
  createdAt: Date            // Indexing timestamp
}
```

### Document Collection
```typescript
{
  embedding: number[],       // Multimodal embedding
  documentType: string,      // Document type
  documentMetadata: object,  // Document metadata
  createdAt: Date            // Indexing timestamp
}
```

## Troubleshooting

### Common Issues

1. **MongoDB Connection**: Ensure MongoDB is running and accessible
2. **Search Indexes**: Verify that search indexes are created before using search features
3. **Environment Variables**: Check that all required environment variables are set
4. **Google Cloud**: Ensure proper authentication and API access
5. **PDF Processing**: Ensure PDF files are available in the data directory

### Search Index Requirements

For text search, create a search index on the `data` field:
```json
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "data": {
        "type": "string",
        "analyzer": "lucene.english"
      }
    }
  }
}
```

For vector search, create a search index on the embedding field:
```json
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": {
        "type": "vector",
        "dimensions": 768,
        "similarity": "cosine"
      }
    }
  }
}
```

### Retry Configuration

The application demonstrates retry configuration at the component level:

- **Indexer**: 3 retry attempts with 1000ms base delay and 0.1 jitter factor
- **Retriever**: 2 retry attempts with 500ms base delay
- **CRUD Tools**: No retry configuration (uses defaults)
- **Search Index Tools**: No retry configuration (uses defaults)

## License

Apache 2.0

This test application demonstrates the capabilities of the MongoDB plugin for Genkit. For more information about the plugin, see the [plugin documentation](../plugins/mongodb/README.md).