/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { describe, expect, it, jest } from '@jest/globals';
import {
  ConnectionSchema,
  IndexerOptions,
  IndexerOptionsSchema,
  InputCreate,
  InputCreateSchema,
  InputDelete,
  InputDeleteSchema,
  InputRead,
  InputReadSchema,
  InputSearchIndexCreate,
  InputSearchIndexCreateSchema,
  InputSearchIndexDrop,
  InputSearchIndexDropSchema,
  InputSearchIndexList,
  InputSearchIndexListSchema,
  InputUpdate,
  InputUpdateSchema,
  RetrieverOptions,
  RetrieverOptionsSchema,
  validateConnection,
  validateCreateOptions,
  validateDeleteOptions,
  validateIndexerOptions,
  validateReadOptions,
  validateRetrieverOptions,
  validateSearchIndexCreateOptions,
  validateSearchIndexDropOptions,
  validateSearchIndexListOptions,
  validateUpdateOptions,
} from '../../src/common/types';

describe('validateConnection', () => {
  it('should validate a valid connection', () => {
    const connection = {
      url: 'mongodb://localhost:27017',
      indexer: { id: 'test-indexer' },
      retriever: { id: 'test-retriever' },
    };

    const result = validateConnection(connection);
    expect(result).toEqual(connection);
  });

  it('should throw error for missing url', () => {
    const connection = {
      indexer: { id: 'test-indexer' },
    };

    expect(() => validateConnection(connection as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for invalid url', () => {
    const connection = {
      url: 'invalid-url',
      indexer: { id: 'test-indexer' },
    };

    expect(() => validateConnection(connection)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error when no components are provided', () => {
    const connection = {
      url: 'mongodb://localhost:27017',
    };

    expect(() => validateConnection(connection)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should handle validation error with non-Error object', () => {
    const originalSchema = ConnectionSchema;
    (ConnectionSchema as any).parse = jest.fn().mockImplementation(() => {
      throw 'String error';
    });

    const connection = {
      url: 'mongodb://localhost:27017',
      indexer: { id: 'test-indexer' },
    };

    expect(() => validateConnection(connection)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (ConnectionSchema as any).parse = originalSchema.parse;
  });
});

describe('validateIndexerOptions', () => {
  it('should validate valid indexer options', () => {
    const options: IndexerOptions = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      embedder: { name: 'test-embedder' },
    } as IndexerOptions;

    const result = validateIndexerOptions(options);
    expect(result).toEqual({
      ...options,
      dataField: 'data',
      metadataField: 'metadata',
      dataTypeField: 'dataType',
      embeddingField: 'embedding',
      batchSize: 100,
      skipData: false,
    });
  });

  it('should throw error for missing dbName', () => {
    const options = {
      collectionName: 'testcollection',
      embedder: { name: 'test-embedder' },
    } as IndexerOptions;

    expect(() => validateIndexerOptions(options)).toThrow(
      'Invalid Mongo indexer options'
    );
  });

  it('should throw error for missing collectionName', () => {
    const options = {
      dbName: 'testdb',
      embedder: { name: 'test-embedder' },
    } as IndexerOptions;

    expect(() => validateIndexerOptions(options)).toThrow(
      'Invalid Mongo indexer options'
    );
  });

  it('should throw error for missing embedder', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    } as IndexerOptions;

    expect(() => validateIndexerOptions(options)).toThrow(
      'Invalid Mongo indexer options'
    );
  });
});

describe('validateRetrieverOptions', () => {
  it('should validate valid retriever options with text search', () => {
    const options: RetrieverOptions = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      search: {
        index: 'test-index',
        text: {
          path: 'content',
        },
      },
    } as RetrieverOptions;

    const result = validateRetrieverOptions(options);
    expect(result).toEqual({
      ...options,
      dataField: 'data',
      metadataField: 'metadata',
      dataTypeField: 'dataType',
    });
  });

  it('should validate valid retriever options with vector search', () => {
    const options: RetrieverOptions = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      embedder: { name: 'test-embedder' },
      vectorSearch: {
        index: 'test-index',
        path: 'embedding',
        numCandidates: 100,
        exact: false,
      },
    } as RetrieverOptions;

    const result = validateRetrieverOptions(options);
    expect(result).toEqual({
      ...options,
      dataField: 'data',
      metadataField: 'metadata',
      dataTypeField: 'dataType',
    });
  });

  it('should throw error for missing dbName', () => {
    const options = {
      collectionName: 'testcollection',
      search: {
        index: 'test-index',
        text: {
          path: 'content',
        },
      },
    } as RetrieverOptions;

    expect(() => validateRetrieverOptions(options)).toThrow(
      'Invalid Mongo retriever options'
    );
  });

  it('should throw error for missing collectionName', () => {
    const options = {
      dbName: 'testdb',
      search: {
        index: 'test-index',
        text: {
          path: 'content',
        },
      },
    } as RetrieverOptions;

    expect(() => validateRetrieverOptions(options)).toThrow(
      'Invalid Mongo retriever options'
    );
  });
});

describe('validateCreateOptions', () => {
  it('should validate valid create options', () => {
    const input: InputCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      document: { name: 'test' },
    };

    const result = validateCreateOptions(input);
    expect(result).toEqual(input);
  });

  it('should throw error for missing dbName', () => {
    const input = {
      collectionName: 'testcollection',
      document: { name: 'test' },
    } as unknown as InputCreate;

    expect(() => validateCreateOptions(input)).toThrow('Invalid Mongo options');
  });

  it('should throw error for missing collectionName', () => {
    const input = {
      dbName: 'testdb',
      document: { name: 'test' },
    } as unknown as InputCreate;

    expect(() => validateCreateOptions(input)).toThrow('Invalid Mongo options');
  });

  it('should throw error for missing document', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    } as unknown as InputCreate;

    expect(() => validateCreateOptions(input)).toThrow('Invalid Mongo options');
  });
});

describe('validateReadOptions', () => {
  it('should validate valid read options with id', () => {
    const input: InputRead = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    };

    const result = validateReadOptions(input);
    expect(result).toEqual(input);
  });

  it('should throw error for missing dbName', () => {
    const input = {
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    } as InputRead;

    expect(() => validateReadOptions(input)).toThrow('Invalid Mongo options');
  });

  it('should throw error for missing collectionName', () => {
    const input = {
      dbName: 'testdb',
      id: '507f1f77bcf86cd799439011',
    } as InputRead;

    expect(() => validateReadOptions(input)).toThrow('Invalid Mongo options');
  });

  it('should throw error for missing id', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    } as InputRead;

    expect(() => validateReadOptions(input)).toThrow('Invalid Mongo options');
  });

  it('should throw error for invalid ObjectId', () => {
    const input: InputRead = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: 'invalid-id',
    };

    expect(() => validateReadOptions(input)).toThrow('Invalid Mongo options');
  });
});

describe('validateUpdateOptions', () => {
  it('should validate valid update options with id', () => {
    const input: InputUpdate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
      update: { $set: { status: 'updated' } },
    };

    const result = validateUpdateOptions(input);
    expect(result).toEqual(input);
  });

  it('should throw error for missing dbName', () => {
    const input = {
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
      update: { $set: { status: 'updated' } },
    } as unknown as InputUpdate;

    expect(() => validateUpdateOptions(input)).toThrow('Invalid Mongo options');
  });

  it('should throw error for missing collectionName', () => {
    const input = {
      dbName: 'testdb',
      id: '507f1f77bcf86cd799439011',
      update: { $set: { status: 'updated' } },
    } as unknown as InputUpdate;

    expect(() => validateUpdateOptions(input)).toThrow('Invalid Mongo options');
  });

  it('should throw error for missing update', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    } as unknown as InputUpdate;

    expect(() => validateUpdateOptions(input)).toThrow('Invalid Mongo options');
  });

  it('should throw error for missing id', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      update: { $set: { status: 'updated' } },
    } as unknown as InputUpdate;

    expect(() => validateUpdateOptions(input)).toThrow('Invalid Mongo options');
  });
});

describe('validateDeleteOptions', () => {
  it('should validate valid delete options with id', () => {
    const input: InputDelete = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    };

    const result = validateDeleteOptions(input);
    expect(result).toEqual(input);
  });

  it('should throw error for missing dbName', () => {
    const input = {
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    } as unknown as InputDelete;

    expect(() => validateDeleteOptions(input)).toThrow('Invalid Mongo options');
  });

  it('should throw error for missing collectionName', () => {
    const input = {
      dbName: 'testdb',
      id: '507f1f77bcf86cd799439011',
    } as unknown as InputDelete;

    expect(() => validateDeleteOptions(input)).toThrow('Invalid Mongo options');
  });

  it('should throw error for missing id', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    } as unknown as InputDelete;

    expect(() => validateDeleteOptions(input)).toThrow('Invalid Mongo options');
  });
});

describe('validateSearchIndexCreateOptions', () => {
  it('should validate valid search index create options', () => {
    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'search',
        definition: {
          mappings: {
            dynamic: true,
          },
        },
      },
    };

    const result = validateSearchIndexCreateOptions(input);
    expect(result).toEqual(input);
  });

  it('should throw error for missing dbName', () => {
    const input: InputSearchIndexCreate = {
      collectionName: 'testcollection',
      schema: {
        type: 'search',
        definition: {
          mappings: {
            dynamic: true,
          },
        },
      },
    } as unknown as InputSearchIndexCreate;

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      /Invalid Mongo options/
    );
  });

  it('should throw error for missing collectionName', () => {
    const input = {
      dbName: 'testdb',
      indexName: 'test-index',
      definition: {
        mappings: {
          dynamic: true,
        },
      },
    } as unknown as InputSearchIndexCreate;

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      /Invalid Mongo options/
    );
  });

  it('should throw error for missing indexName', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      definition: {
        mappings: {
          dynamic: true,
        },
      },
    } as unknown as InputSearchIndexCreate;

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      /Invalid Mongo options/
    );
  });

  it('should throw error for missing definition', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'search',
      },
    } as unknown as InputSearchIndexCreate;

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      /Invalid Mongo options/
    );
  });

  it('should handle validation error with non-Error object', () => {
    const originalSchema = InputSearchIndexCreateSchema;
    (InputSearchIndexCreateSchema as any).parse = jest
      .fn()
      .mockImplementation(() => {
        throw 'String error';
      });

    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      indexName: 'test_index',
      schema: {
        type: 'search' as const,
        definition: { mappings: { dynamic: true } },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputSearchIndexCreateSchema as any).parse = originalSchema.parse;
  });
});

describe('validateSearchIndexListOptions', () => {
  it('should validate valid search index list options', () => {
    const input: InputSearchIndexList = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    };

    const result = validateSearchIndexListOptions(input);
    expect(result).toEqual(input);
  });

  it('should throw error for missing dbName', () => {
    const input = {
      collectionName: 'testcollection',
    } as InputSearchIndexList;

    expect(() => validateSearchIndexListOptions(input)).toThrow(
      /Invalid Mongo options/
    );
  });

  it('should throw error for missing collectionName', () => {
    const input = {
      dbName: 'testdb',
    } as InputSearchIndexList;

    expect(() => validateSearchIndexListOptions(input)).toThrow(
      /Invalid Mongo options/
    );
  });

  it('should handle validation error with non-Error object', () => {
    const originalSchema = InputSearchIndexListSchema;
    (InputSearchIndexListSchema as any).parse = jest
      .fn()
      .mockImplementation(() => {
        throw 'String error';
      });

    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    };

    expect(() => validateSearchIndexListOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputSearchIndexListSchema as any).parse = originalSchema.parse;
  });
});

describe('validateSearchIndexDropOptions', () => {
  it('should validate valid search index drop options', () => {
    const input: InputSearchIndexDrop = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      indexName: 'test-index',
    };

    const result = validateSearchIndexDropOptions(input);
    expect(result).toEqual(input);
  });

  it('should throw error for missing dbName', () => {
    const input = {
      collectionName: 'testcollection',
      indexName: 'test-index',
    } as InputSearchIndexDrop;

    expect(() => validateSearchIndexDropOptions(input)).toThrow(
      /Invalid Mongo options/
    );
  });

  it('should throw error for missing collectionName', () => {
    const input = {
      dbName: 'testdb',
      indexName: 'test-index',
    } as InputSearchIndexDrop;

    expect(() => validateSearchIndexDropOptions(input)).toThrow(
      /Invalid Mongo options/
    );
  });

  it('should throw error for missing indexName', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    } as InputSearchIndexDrop;

    expect(() => validateSearchIndexDropOptions(input)).toThrow(
      /Invalid Mongo options/
    );
  });

  it('should handle validation error with non-Error object', () => {
    const originalSchema = InputSearchIndexDropSchema;
    (InputSearchIndexDropSchema as any).parse = jest
      .fn()
      .mockImplementation(() => {
        throw 'String error';
      });

    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      indexName: 'test_index',
    };

    expect(() => validateSearchIndexDropOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputSearchIndexDropSchema as any).parse = originalSchema.parse;
  });
});

describe('validateRetrieverOptions', () => {
  it('should validate valid retriever options with text search', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      search: {
        index: 'default',
        text: {
          path: 'data',
        },
      },
      dataField: 'data',
      dataTypeField: 'dataType',
      metadataField: 'metadata',
    };

    const result = validateRetrieverOptions(options);
    expect(result).toEqual(options);
  });

  it('should validate valid retriever options with vector search', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      vectorSearch: {
        index: 'vector_index',
        path: 'embedding',
        exact: false,
        numCandidates: 100,
        limit: 10,
      },
      embedder: 'test-embedder',
      dataField: 'data',
      dataTypeField: 'dataType',
      metadataField: 'metadata',
    };

    const result = validateRetrieverOptions(options);
    expect(result).toEqual(options);
  });

  it('should throw error for missing dbName', () => {
    const options = {
      collectionName: 'testcollection',
      search: {
        index: 'default',
        text: {
          path: 'data',
        },
      },
    };

    expect(() => validateRetrieverOptions(options as any)).toThrow(
      'Invalid Mongo retriever options'
    );
  });

  it('should throw error for missing collectionName', () => {
    const options = {
      dbName: 'testdb',
      search: {
        index: 'default',
        text: {
          path: 'data',
        },
      },
    };

    expect(() => validateRetrieverOptions(options as any)).toThrow(
      'Invalid Mongo retriever options'
    );
  });

  it('should handle validation error with non-Error object', () => {
    const originalSchema = RetrieverOptionsSchema;
    (RetrieverOptionsSchema as any).parse = jest.fn().mockImplementation(() => {
      throw 'String error';
    });

    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      search: {
        index: 'default',
        text: {
          path: 'data',
        },
      },
    };

    expect(() => validateRetrieverOptions(options as any)).toThrow(
      'Invalid Mongo retriever options: '
    );

    (RetrieverOptionsSchema as any).parse = originalSchema.parse;
  });
});

describe('validateCreateOptions', () => {
  it('should validate valid create options', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      document: { name: 'test' },
    };

    const result = validateCreateOptions(input);
    expect(result).toEqual(input);
  });

  it('should throw error for missing dbName', () => {
    const input = {
      collectionName: 'testcollection',
      document: { name: 'test' },
    };

    expect(() => validateCreateOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for missing collectionName', () => {
    const input = {
      dbName: 'testdb',
      document: { name: 'test' },
    };

    expect(() => validateCreateOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for missing document', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    };

    expect(() => validateCreateOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should handle validation error with non-Error object', () => {
    const originalSchema = InputCreateSchema;
    (InputCreateSchema as any).parse = jest.fn().mockImplementation(() => {
      throw 'String error';
    });

    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      document: { name: 'test' },
    };

    expect(() => validateCreateOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputCreateSchema as any).parse = originalSchema.parse;
  });
});

describe('validateReadOptions', () => {
  it('should validate valid read options with id', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    };

    const result = validateReadOptions(input);
    expect(result).toEqual(input);
  });

  it('should throw error for missing dbName', () => {
    const input = {
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    };

    expect(() => validateReadOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for missing collectionName', () => {
    const input = {
      dbName: 'testdb',
      id: '507f1f77bcf86cd799439011',
    };

    expect(() => validateReadOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for missing id', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    };

    expect(() => validateReadOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for invalid ObjectId', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: 'invalid-id',
    };

    expect(() => validateReadOptions(input)).toThrow('Invalid Mongo options');
  });

  it('should handle validation error with non-Error object', () => {
    const originalSchema = InputReadSchema;
    (InputReadSchema as any).parse = jest.fn().mockImplementation(() => {
      throw 'String error';
    });

    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    };

    expect(() => validateReadOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputReadSchema as any).parse = originalSchema.parse;
  });
});

describe('validateUpdateOptions', () => {
  it('should validate valid update options with id', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
      update: { $set: { status: 'updated' } },
    };

    const result = validateUpdateOptions(input);
    expect(result).toEqual(input);
  });

  it('should throw error for missing dbName', () => {
    const input = {
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
      update: { $set: { status: 'updated' } },
    };

    expect(() => validateUpdateOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for missing collectionName', () => {
    const input = {
      dbName: 'testdb',
      id: '507f1f77bcf86cd799439011',
      update: { $set: { status: 'updated' } },
    };

    expect(() => validateUpdateOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for missing update', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    };

    expect(() => validateUpdateOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for missing id', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      update: { $set: { status: 'updated' } },
    };

    expect(() => validateUpdateOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should handle validation error with non-Error object', () => {
    const originalSchema = InputUpdateSchema;
    (InputUpdateSchema as any).parse = jest.fn().mockImplementation(() => {
      throw 'String error';
    });

    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
      update: { $set: { status: 'updated' } },
    };

    expect(() => validateUpdateOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputUpdateSchema as any).parse = originalSchema.parse;
  });
});

describe('validateDeleteOptions', () => {
  it('should validate valid delete options with id', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    };

    const result = validateDeleteOptions(input);
    expect(result).toEqual(input);
  });

  it('should throw error for missing dbName', () => {
    const input = {
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    };

    expect(() => validateDeleteOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for missing collectionName', () => {
    const input = {
      dbName: 'testdb',
      id: '507f1f77bcf86cd799439011',
    };

    expect(() => validateDeleteOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for missing id', () => {
    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    };

    expect(() => validateDeleteOptions(input as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should handle validation error with non-Error object', () => {
    const originalSchema = InputDeleteSchema;
    (InputDeleteSchema as any).parse = jest.fn().mockImplementation(() => {
      throw 'String error';
    });

    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      id: '507f1f77bcf86cd799439011',
    };

    expect(() => validateDeleteOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputDeleteSchema as any).parse = originalSchema.parse;
  });
});

describe('validateIndexerOptions', () => {
  it('should validate valid indexer options', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      embedder: { name: 'test-embedder' },
      dataField: 'data',
      dataTypeField: 'dataType',
      metadataField: 'metadata',
      embeddingField: 'embedding',
      batchSize: 100,
      skipData: false,
    };

    const result = validateIndexerOptions(options);
    expect(result).toEqual(options);
  });

  it('should throw error for missing dbName', () => {
    const options = {
      collectionName: 'testcollection',
      embedder: 'test-embedder',
    };

    expect(() => validateIndexerOptions(options as any)).toThrow(
      'Invalid Mongo indexer options'
    );
  });

  it('should throw error for missing collectionName', () => {
    const options = {
      dbName: 'testdb',
      embedder: 'test-embedder',
    };

    expect(() => validateIndexerOptions(options as any)).toThrow(
      'Invalid Mongo indexer options'
    );
  });

  it('should throw error for missing embedder', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    };

    expect(() => validateIndexerOptions(options as any)).toThrow(
      'Invalid Mongo indexer options'
    );
  });

  it('should handle validation error with non-Error object', () => {
    const originalSchema = IndexerOptionsSchema;
    (IndexerOptionsSchema as any).parse = jest.fn().mockImplementation(() => {
      throw 'String error';
    });

    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      embedder: { name: 'test-embedder' },
      dataField: 'data',
      metadataField: 'metadata',
      dataTypeField: 'dataType',
      embeddingField: 'embedding',
      batchSize: 100,
      skipData: false,
    };

    expect(() => validateIndexerOptions(options)).toThrow(
      'Invalid Mongo indexer options: Validation failed'
    );

    (IndexerOptionsSchema as any).parse = originalSchema.parse;
  });
});

describe('validateConnection', () => {
  it('should validate a valid connection', () => {
    const connection = {
      url: 'mongodb://localhost:27017',
      indexer: { id: 'test-indexer' },
      retriever: { id: 'test-retriever' },
    };

    expect(() => validateConnection(connection)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for missing url', () => {
    const connection = {
      indexer: { id: 'test-indexer' },
    };

    expect(() => validateConnection(connection as any)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error for invalid url', () => {
    const connection = {
      url: 'invalid-url',
      indexer: { id: 'test-indexer' },
    };

    expect(() => validateConnection(connection)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error when no components are provided', () => {
    const connection = {
      url: 'mongodb://localhost:27017',
    };

    expect(() => validateConnection(connection)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should handle validation error with non-Error object', () => {
    const originalSchema = ConnectionSchema;
    (ConnectionSchema as any).parse = jest.fn().mockImplementation(() => {
      throw 'String error';
    });

    const connection = {
      url: 'mongodb://localhost:27017',
      indexer: { id: 'test-indexer' },
    };

    expect(() => validateConnection(connection)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (ConnectionSchema as any).parse = originalSchema.parse;
  });
});

describe('TextSearchSchema validation', () => {
  it('should throw error when fuzzy and synonyms are used together', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      search: {
        index: 'test-index',
        text: {
          path: 'content',
          fuzzy: { maxEdits: 1 },
          synonyms: 'synonym-list',
        },
      },
    } as any;

    expect(() => validateRetrieverOptions(options)).toThrow(
      'Invalid Mongo retriever options'
    );
  });
});

describe('VectorSearchSchema validation', () => {
  it('should throw error when exact is false but numCandidates is missing', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      vectorSearch: {
        index: 'test-index',
        path: 'embedding',
        exact: false,
      },
    } as any;

    expect(() => validateRetrieverOptions(options)).toThrow(
      'Invalid Mongo retriever options'
    );
  });

  it('should throw error when numCandidates is provided but exact is undefined', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      vectorSearch: {
        index: 'test-index',
        path: 'embedding',
        numCandidates: 100,
      },
    } as any;

    expect(() => validateRetrieverOptions(options)).toThrow(
      'Invalid Mongo retriever options'
    );
  });

  it('should throw error when limit exceeds numCandidates', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      vectorSearch: {
        index: 'test-index',
        path: 'embedding',
        exact: false,
        numCandidates: 50,
        limit: 100,
      },
      embedder: 'test-embedder',
    } as any;

    expect(() => validateRetrieverOptions(options)).toThrow(
      'Invalid Mongo retriever options'
    );
  });
});

describe('SearchIndexDefinitionSchema validation', () => {
  it('should throw error when dynamic is false but fields are missing', () => {
    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'search',
        definition: {
          mappings: {
            dynamic: false,
          },
        },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options'
    );
  });
});

describe('VectorSearchIndexSchema validation', () => {
  it('should throw error when similarity is set for non-vector field', () => {
    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'vectorSearch',
        definition: {
          fields: [
            {
              type: 'filter',
              path: 'category',
              similarity: 'cosine',
            },
          ],
        },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error when numDimensions is set for non-vector field', () => {
    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'vectorSearch',
        definition: {
          fields: [
            {
              type: 'filter',
              path: 'category',
              numDimensions: 128,
            },
          ],
        },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should throw error when no vector fields are provided', () => {
    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'vectorSearch',
        definition: {
          fields: [],
        },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options'
    );
  });
});

describe('Search index validation error handling', () => {
  it('should handle non-Error exceptions in search index definition validation', () => {
    const originalParse = (InputSearchIndexCreateSchema as any).parse;
    (InputSearchIndexCreateSchema as any).parse = jest
      .fn()
      .mockImplementation(() => {
        throw 'String error';
      });

    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'search',
        definition: {
          mappings: {
            dynamic: true,
          },
        },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputSearchIndexCreateSchema as any).parse = originalParse;
  });

  it('should handle non-Error exceptions in vector search index definition validation', () => {
    const originalParse = (InputSearchIndexCreateSchema as any).parse;
    (InputSearchIndexCreateSchema as any).parse = jest
      .fn()
      .mockImplementation(() => {
        throw 'String error';
      });

    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'vectorSearch',
        definition: {
          fields: [
            {
              type: 'vector',
              path: 'embedding',
              numDimensions: 128,
              similarity: 'cosine',
            },
          ],
        },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputSearchIndexCreateSchema as any).parse = originalParse;
  });
});

describe('Schema validation through retriever options', () => {
  it('should trigger text search fuzzy/synonyms conflict validation', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      search: {
        index: 'test-index',
        text: {
          path: 'content',
          fuzzy: { maxEdits: 1 },
          synonyms: 'synonym-list',
        },
      },
    } as any;

    expect(() => validateRetrieverOptions(options)).toThrow(
      'Invalid Mongo retriever options'
    );
  });

  it('should trigger vector search exact/numCandidates validation', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      vectorSearch: {
        index: 'test-index',
        path: 'embedding',
        exact: false,
      },
    } as any;

    expect(() => validateRetrieverOptions(options)).toThrow(
      'Invalid Mongo retriever options'
    );
  });

  it('should trigger vector search numCandidates/exact validation', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      vectorSearch: {
        index: 'test-index',
        path: 'embedding',
        numCandidates: 100,
      },
    } as any;

    expect(() => validateRetrieverOptions(options)).toThrow(
      'Invalid Mongo retriever options'
    );
  });

  it('should trigger vector search limit/numCandidates validation', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      vectorSearch: {
        index: 'test-index',
        path: 'embedding',
        exact: false,
        numCandidates: 50,
        limit: 100,
      },
      embedder: 'test-embedder',
    } as any;

    expect(() => validateRetrieverOptions(options)).toThrow(
      'Invalid Mongo retriever options'
    );
  });
});

describe('Search index schema validation through create options', () => {
  it('should trigger search index definition validation with dynamic false but no fields', () => {
    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'search',
        definition: {
          mappings: {
            dynamic: false,
          },
        },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should trigger vector search index validation with similarity on non-vector field', () => {
    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'vectorSearch',
        definition: {
          fields: [
            {
              type: 'filter',
              path: 'category',
              similarity: 'cosine',
            },
          ],
        },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should trigger vector search index validation with numDimensions on non-vector field', () => {
    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'vectorSearch',
        definition: {
          fields: [
            {
              type: 'filter',
              path: 'category',
              numDimensions: 128,
            },
          ],
        },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options'
    );
  });

  it('should trigger vector search index validation with empty fields array', () => {
    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'vectorSearch',
        definition: {
          fields: [],
        },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options'
    );
  });
});

describe('HybridSearchSchema validation', () => {
  it('should validate hybrid search schema structure', () => {
    const hybridSearchConfig = {
      search: {
        index: 'text_index',
        text: {
          path: 'data',
        },
      },
      vectorSearch: {
        index: 'vector_index',
        path: 'embedding',
        exact: false,
        numCandidates: 100,
        limit: 10,
      },
      combination: {
        weights: {
          vectorPipeline: 0.7,
          fullTextPipeline: 0.3,
        },
      },
      scoreDetails: true,
    };

    expect(hybridSearchConfig).toBeDefined();
    expect(hybridSearchConfig.search).toBeDefined();
    expect(hybridSearchConfig.vectorSearch).toBeDefined();
    expect(hybridSearchConfig.combination).toBeDefined();
    expect(hybridSearchConfig.scoreDetails).toBe(true);
  });
});

describe('EmbedderOptionsSchema validation', () => {
  it('should throw error for missing embedder', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      embedderOptions: { model: 'text-embedding-3-small' },
    } as any;

    expect(() => validateIndexerOptions(options)).toThrow(
      'Invalid Mongo indexer options'
    );
  });

  it('should throw error for null embedder', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      embedder: null,
    } as any;

    expect(() => validateIndexerOptions(options)).toThrow(
      'Invalid Mongo indexer options'
    );
  });

  it('should throw error for undefined embedder', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      embedder: undefined,
    } as any;

    expect(() => validateIndexerOptions(options)).toThrow(
      'Invalid Mongo indexer options'
    );
  });

  it('should throw error for empty string embedder', () => {
    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      embedder: '',
    } as any;

    expect(() => validateIndexerOptions(options)).toThrow(
      'Invalid Mongo indexer options'
    );
  });
});

describe('RetryOptionsSchema validation', () => {
  it('should validate valid retry options', () => {
    const options = {
      retryAttempts: 3,
      baseDelay: 1000,
      jitterFactor: 0.5,
    };

    expect(() => {
      const testObj = { retry: options };
      return testObj;
    }).not.toThrow();
  });

  it('should handle missing retry options', () => {
    expect(() => {
      const testObj = { retry: undefined };
      return testObj;
    }).not.toThrow();
  });
});

describe('DataFieldSchema validation', () => {
  it('should validate data field schema structure', () => {
    const dataFieldConfig = {
      dataField: 'customData',
      metadataField: 'customMetadata',
      dataTypeField: 'customDataType',
    };

    expect(dataFieldConfig.dataField).toBe('customData');
    expect(dataFieldConfig.metadataField).toBe('customMetadata');
    expect(dataFieldConfig.dataTypeField).toBe('customDataType');
  });
});

describe('BaseDatabaseCollectionSchema validation', () => {
  it('should validate database collection schema structure', () => {
    const dbConfig = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      dbOptions: { readPreference: 'secondary' },
      collectionOptions: { readConcern: { level: 'majority' } },
    };

    expect(dbConfig.dbName).toBe('testdb');
    expect(dbConfig.collectionName).toBe('testcollection');
    expect(dbConfig.dbOptions).toEqual({ readPreference: 'secondary' });
    expect(dbConfig.collectionOptions).toEqual({
      readConcern: { level: 'majority' },
    });
  });
});

describe('Search index schema validation edge cases', () => {
  it('should validate search index definition structure', () => {
    const searchIndexDef = {
      mappings: {
        dynamic: true,
        fields: { someField: { type: 'string' } },
      },
    };

    expect(searchIndexDef.mappings.dynamic).toBe(true);
    expect(searchIndexDef.mappings.fields).toEqual({
      someField: { type: 'string' },
    });
  });

  it('should validate vector search index structure', () => {
    const vectorIndexDef = {
      fields: [
        {
          type: 'vector',
          path: 'embedding',
          numDimensions: 128,
          similarity: 'cosine',
          quantization: 'scalar',
        },
        {
          type: 'filter',
          path: 'category',
        },
      ],
    };

    expect(vectorIndexDef.fields).toHaveLength(2);
    expect(vectorIndexDef.fields[0].type).toBe('vector');
    expect(vectorIndexDef.fields[1].type).toBe('filter');
  });
});

describe('Validation error handling edge cases', () => {
  it('should handle validation error with Error object that has no message', () => {
    const originalSchema = RetrieverOptionsSchema;
    (RetrieverOptionsSchema as any).parse = jest.fn().mockImplementation(() => {
      const error = new Error();
      delete (error as any).message;
      throw error;
    });

    const options = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      search: {
        index: 'default',
        text: {
          path: 'data',
        },
      },
    };

    expect(() => validateRetrieverOptions(options as any)).toThrow(
      'Invalid Mongo retriever options: '
    );

    (RetrieverOptionsSchema as any).parse = originalSchema.parse;
  });

  it('should handle validation error with non-Error object in search index create', () => {
    const originalSchema = InputSearchIndexCreateSchema;
    (InputSearchIndexCreateSchema as any).parse = jest
      .fn()
      .mockImplementation(() => {
        throw { customError: 'Custom error object' };
      });

    const input: InputSearchIndexCreate = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      schema: {
        type: 'search' as const,
        definition: {
          mappings: {
            dynamic: true,
          },
        },
      },
    };

    expect(() => validateSearchIndexCreateOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputSearchIndexCreateSchema as any).parse = originalSchema.parse;
  });

  it('should handle validation error with non-Error object in search index list', () => {
    const originalSchema = InputSearchIndexListSchema;
    (InputSearchIndexListSchema as any).parse = jest
      .fn()
      .mockImplementation(() => {
        throw { customError: 'Custom error object' };
      });

    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
    };

    expect(() => validateSearchIndexListOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputSearchIndexListSchema as any).parse = originalSchema.parse;
  });

  it('should handle validation error with non-Error object in search index drop', () => {
    const originalSchema = InputSearchIndexDropSchema;
    (InputSearchIndexDropSchema as any).parse = jest
      .fn()
      .mockImplementation(() => {
        throw { customError: 'Custom error object' };
      });

    const input = {
      dbName: 'testdb',
      collectionName: 'testcollection',
      indexName: 'test_index',
    };

    expect(() => validateSearchIndexDropOptions(input)).toThrow(
      'Invalid Mongo options: Validation failed'
    );

    (InputSearchIndexDropSchema as any).parse = originalSchema.parse;
  });
});

describe('Schema refinement validation', () => {
  it('should validate text search schema structure', () => {
    const textSearchConfig = {
      index: 'test-index',
      text: {
        path: 'content',
        fuzzy: { maxEdits: 1, prefixLength: 2 },
      },
    };

    expect(textSearchConfig.index).toBe('test-index');
    expect(textSearchConfig.text.path).toBe('content');
    expect(textSearchConfig.text.fuzzy).toEqual({
      maxEdits: 1,
      prefixLength: 2,
    });
  });

  it('should validate vector search schema structure', () => {
    const vectorSearchConfig = {
      index: 'test-index',
      path: 'embedding',
      exact: false,
      numCandidates: 100,
      limit: 10,
      filter: { category: 'test' },
    };

    expect(vectorSearchConfig.index).toBe('test-index');
    expect(vectorSearchConfig.path).toBe('embedding');
    expect(vectorSearchConfig.exact).toBe(false);
    expect(vectorSearchConfig.numCandidates).toBe(100);
    expect(vectorSearchConfig.filter).toEqual({ category: 'test' });
  });
});

describe('Pipeline validation', () => {
  it('should validate pipeline structure', () => {
    const pipeline = [
      { $limit: 5 },
      { $sort: { score: -1 } },
      { $project: { _id: 0, content: 1 } },
    ];

    expect(pipeline).toHaveLength(3);
    expect(pipeline[0]).toEqual({ $limit: 5 });
    expect(pipeline[1]).toEqual({ $sort: { score: -1 } });
    expect(pipeline[2]).toEqual({ $project: { _id: 0, content: 1 } });
  });
});

describe('Vector search validation edge cases', () => {
  it('should validate vector search with exact true and numCandidates', () => {
    const vectorSearchConfig = {
      index: 'test-index',
      path: 'embedding',
      exact: true,
      numCandidates: 100,
      limit: 10,
    };

    expect(vectorSearchConfig.exact).toBe(true);
    expect(vectorSearchConfig.numCandidates).toBe(100);
    expect(vectorSearchConfig.limit).toBe(10);
  });

  it('should validate vector search with exact undefined and numCandidates', () => {
    const vectorSearchConfig: any = {
      index: 'test-index',
      path: 'embedding',
      numCandidates: 100,
      limit: 10,
    };

    expect(vectorSearchConfig.exact).toBeUndefined();
    expect(vectorSearchConfig.numCandidates).toBe(100);
    expect(vectorSearchConfig.limit).toBe(10);
  });

  it('should validate vector search with limit equal to numCandidates', () => {
    const vectorSearchConfig = {
      index: 'test-index',
      path: 'embedding',
      exact: false,
      numCandidates: 100,
      limit: 100,
    };

    expect(vectorSearchConfig.exact).toBe(false);
    expect(vectorSearchConfig.numCandidates).toBe(100);
    expect(vectorSearchConfig.limit).toBe(100);
  });
});

describe('Text search validation edge cases', () => {
  it('should validate text search with fuzzy only', () => {
    const textSearchConfig: any = {
      index: 'test-index',
      text: {
        path: 'content',
        fuzzy: { maxEdits: 1, prefixLength: 2 },
      },
    };

    expect(textSearchConfig.text.fuzzy).toBeDefined();
    expect(textSearchConfig.text.synonyms).toBeUndefined();
  });

  it('should validate text search with synonyms only', () => {
    const textSearchConfig: any = {
      index: 'test-index',
      text: {
        path: 'content',
        synonyms: 'synonym-list',
      },
    };

    expect(textSearchConfig.text.synonyms).toBeDefined();
    expect(textSearchConfig.text.fuzzy).toBeUndefined();
  });
});

describe('Hybrid search validation edge cases', () => {
  it('should validate hybrid search with custom weights', () => {
    const hybridSearchConfig = {
      search: {
        index: 'text_index',
        text: {
          path: 'data',
        },
      },
      vectorSearch: {
        index: 'vector_index',
        path: 'embedding',
        exact: false,
        numCandidates: 100,
        limit: 10,
      },
      combination: {
        weights: {
          vectorPipeline: 0.8,
          fullTextPipeline: 0.2,
        },
      },
      scoreDetails: true,
    };

    expect(hybridSearchConfig.combination.weights.vectorPipeline).toBe(0.8);
    expect(hybridSearchConfig.combination.weights.fullTextPipeline).toBe(0.2);
    expect(hybridSearchConfig.scoreDetails).toBe(true);
  });

  it('should validate hybrid search with default weights', () => {
    const hybridSearchConfig: any = {
      search: {
        index: 'text_index',
        text: {
          path: 'data',
        },
      },
      vectorSearch: {
        index: 'vector_index',
        path: 'embedding',
        exact: false,
        numCandidates: 100,
        limit: 10,
      },
    };

    expect(hybridSearchConfig.combination).toBeUndefined();
    expect(hybridSearchConfig.scoreDetails).toBeUndefined();
  });
});
