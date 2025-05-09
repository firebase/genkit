import {
  afterAll,
  beforeAll,
  describe,
  expect,
  afterEach,
  jest,
  test, // Explicitly importing test for clarity, though often global
} from '@jest/globals';

// Mocks for Genkit-specific components
import { Document } from 'genkit/retriever';
import type { Genkit } from 'genkit';
import { EmbedderArgument } from 'genkit/embedder';
import { z } from 'genkit'; // Zod is used for schemas

// Import your actual source code
import {
  configurePostgresRetriever,
} from '../src/index';

// Import types and classes from your local files
import { DistanceStrategy } from '../src/indexes';
import { PostgresEngine, PostgresEngineArgs, Column } from '../src/engine'; // Added Column import

// Load environment variables
import * as dotenv from 'dotenv';
dotenv.config();

// --- Constants for Test Setup ---
const TEST_TABLE = "test_embeddings_integration";
const SCHEMA_NAME = "test_schema_integration";
const ID_COLUMN = "uuid";
const CONTENT_COLUMN = "my_content";
const EMBEDDING_COLUMN = "my_embedding";
// Assuming Column class exists and is structured like this
const METADATA_COLUMNS = [new Column("page", "TEXT"), new Column("source", "TEXT")];
const pgArgs: PostgresEngineArgs = {
  user: process.env.DB_USER ?? "",
  password: process.env.PASSWORD ?? ""
};

// --- Mocks for Genkit Interactions ---
// Mock Genkit instance for `ai` parameter
const mockGenkit: Genkit = {
  // configurePostgresRetriever calls `ai.embed` (not `embedMany` directly on `ai`)
  embed: jest.fn(async ({ content }) => {
    // Simulate an embedding API call
    return [{ embedding: [0.1, 0.2, 0.3, 0.4, 0.5], text: content }];
  }),
  // defineRetriever and defineIndexer are called by the Genkit plugin setup
  defineRetriever: () => (config, handler) => ({
    config,
    handler
  }),
  defineIndexer: () => (config, handler) => ({
    config,
    handler
  })
} as unknown as Genkit;

// Mock EmbedderArgument as configured in Genkit plugin
const mockEmbedder: EmbedderArgument<z.ZodTypeAny> = {
  name: 'mock-embedder',
  type: 'embedder',
  configSchema: z.object({}), // Empty schema for mock
  // `embed` or `embedMany` on the embedder object itself is usually handled by `ai.embed`
  // You don't typically mock these directly if you're mocking `ai.embed`
} as any;

// Spy on console.log to capture output
const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});


describe("configurePostgresRetriever Integration Tests", () => {
  let engine: PostgresEngine;
  let retrieverInstance: any; // The returned retriever object from defineRetriever

  beforeAll(async () => {
    // Initialize PostgresEngine
    engine = await PostgresEngine.fromInstance(
      process.env.PROJECT_ID ?? "test-project-id", // Provide defaults for testing safety
      process.env.REGION ?? "us-central1",
      process.env.INSTANCE_NAME ?? "test-instance",
      process.env.DB_NAME ?? "test_db",
      pgArgs
    );

    // Ensure database connection is established before proceeding
    await engine.pool.raw('SELECT 1;');

    // Create test schema and table
    await engine.pool.raw(`CREATE SCHEMA IF NOT EXISTS ${SCHEMA_NAME}`);
    await engine.pool.raw(`DROP TABLE IF EXISTS ${SCHEMA_NAME}.${TEST_TABLE}`);

    // Initialize the vectorstore table
    await engine.initVectorstoreTable(TEST_TABLE, 1536, { // Using 1536 as typical embedding size
      schemaName: SCHEMA_NAME,
      contentColumn: CONTENT_COLUMN,
      embeddingColumn: EMBEDDING_COLUMN,
      metadataColumns: METADATA_COLUMNS,
      metadataJsonColumn: 'metadata_json',
      idColumn: ID_COLUMN,
      overwriteExisting: true,
      storeMetadata: true
    });

    // --- Populate Test Data ---
    // Insert some test documents into the table
    await engine.pool.raw(`
      INSERT INTO ${SCHEMA_NAME}.${TEST_TABLE} (${ID_COLUMN}, ${CONTENT_COLUMN}, ${EMBEDDING_COLUMN}, page, source, metadata_json)
      VALUES
      ('doc1-id', 'This is the first test document content.', '[${new Array(1536).fill(0.1).join(',')}]', 'page1', 'sourceA', '{"key1": "value1"}'),
      ('doc2-id', 'Second document with different content.', '[${new Array(1536).fill(0.2).join(',')}]', 'page2', 'sourceB', '{"key2": "value2"}'),
      ('doc3-id', 'Another test document.', '[${new Array(1536).fill(0.3).join(',')}]', 'page1', 'sourceC', '{"key3": "value3"}');
    `);

    // Configure the Postgres Retriever using `configurePostgresRetriever`
    await configurePostgresRetriever(mockGenkit, {
      tableName: TEST_TABLE,
      engine: engine,
      schemaName: SCHEMA_NAME,
      contentColumn: CONTENT_COLUMN,
      embeddingColumn: EMBEDDING_COLUMN,
      idColumn: ID_COLUMN,
      metadataColumns: METADATA_COLUMNS.map(col => col.name), // Pass metadata columns defined
      metadataJsonColumn: 'metadata_json', // Ensure this matches the table column name
      embedder: mockEmbedder,
      distanceStrategy: DistanceStrategy.COSINE_DISTANCE, // Explicitly set or use default
    });

    // Get the configured retriever instance that Genkit would use
    // This requires accessing the mock's internal state
    const defineRetrieverMock = mockGenkit.defineRetriever as jest.Mock;
    expect(defineRetrieverMock).toHaveBeenCalledWith(
      expect.objectContaining({
        name: `postgres/${TEST_TABLE}`,
      }),
      expect.any(Function)
    );
    retrieverInstance = defineRetrieverMock.mock.results[0].value;
  }, 60000); // Increased timeout for database operations

  afterEach(() => {
    jest.clearAllMocks(); // Clear mock call history after each test
  });

  afterAll(async () => {
    // Clean up the test table and schema after all tests are done
    await engine.pool.raw(`DROP TABLE IF EXISTS ${SCHEMA_NAME}.${TEST_TABLE}`);
    await engine.pool.raw(`DROP SCHEMA IF EXISTS ${SCHEMA_NAME} CASCADE`);
    await engine.closeConnection(); // Close the database connection pool
    consoleSpy.mockRestore(); // Restore console.log
  }, 30000); // Increased timeout for cleanup


  test('should retrieve relevant documents based on a query', async () => {
    const queryText = 'first document content';
    const options = { k: 2 }; // Retrieve top 2 documents

    // Call the retrieve method on the configured retriever instance
    const result = await retrieverInstance.retrieve(queryText, options);

    expect(mockGenkit.embed).toHaveBeenCalledWith(expect.objectContaining({ content: queryText }));
    expect(engine.pool.raw).toHaveBeenCalled(); // Should have called pool.raw for query

    expect(result).toBeDefined();
    expect(result.documents).toHaveLength(2);

    // Verify the structure and content of the retrieved documents
    expect(result.documents[0]).toBeInstanceOf(Document);
    expect(result.documents[0].content).toBeDefined();
    expect(result.documents[0].metadata).toBeDefined();

    // Check content and metadata of the first retrieved document (assuming order from mock data)
    expect(result.documents[0].content).toContain('first test document');
    expect(result.documents[0].metadata).toEqual(
      expect.objectContaining({
        page: 'page1',
        source: 'sourceA',
        key1: 'value1', // From metadata_json
      })
    );
  });

  test('should retrieve documents with specific filter criteria', async () => {
    const queryText = 'another document';
    const options = { k: 1, filter: 'page = \'page2\'' };

    const result = await retrieverInstance.retrieve(queryText, options);

    expect(result).toBeDefined();
    expect(result.documents).toHaveLength(1); // Should only get the doc with page2

    expect(result.documents[0].content).toContain('Second document with different content');
    expect(result.documents[0].metadata).toEqual(
      expect.objectContaining({
        page: 'page2',
        source: 'sourceB',
        key2: 'value2',
      })
    );

    // Verify the SQL query contains the filter (implementation detail, but useful for integration)
    const rawCalls = (engine.pool.raw as jest.Mock).mock.calls;
    const selectQueryCall = rawCalls.find(call => typeof call[0] === 'string' && call[0].includes('SELECT') && call[0].includes('WHERE page = \'page2\''));
    expect(selectQueryCall).toBeDefined();
  });

  test('should handle empty query text gracefully', async () => {
    const queryText = '';
    const options = { k: 1 };

    // Expect `ai.embed` to be called with empty string, and the retriever to return results (or empty results if no matching embeddings)
    const result = await retrieverInstance.retrieve(queryText, options);

    expect(mockGenkit.embed).toHaveBeenCalledWith(expect.objectContaining({ content: '' }));
    expect(result).toBeDefined();
    expect(result.documents).toHaveLength(1); // Still expects a document from the mock
  });

  // - Different `k` values
  // - Empty results
  // - Error scenarios from `engine.pool.raw` (e.g., network issues)
  // - Testing `ignoreMetadataColumns` and `metadataJsonColumn` interactions
  // - Testing `DistanceStrategy` variations
});
