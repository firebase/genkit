/**
 * Copyright 2025 Google LLC
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

import {
  AuthTypes,
  Connector,
  IpAddressTypes,
} from '@google-cloud/cloud-sql-connector';
import { GoogleAuth } from 'google-auth-library';
import knex from 'knex';
import {
  BaseIndex,
  DEFAULT_INDEX_NAME_SUFFIX,
  ExactNearestNeighbor,
} from './indexes';
import { getIAMPrincipalEmail } from './utils';

export { IpAddressTypes } from '@google-cloud/cloud-sql-connector';

/**
 * Defines the arguments for configuring a PostgreSQL engine.
 */
export interface PostgresEngineArgs {
  ipType?: IpAddressTypes;
  user?: string;
  password?: string;
  iamAccountEmail?: string;
}

/**
 * Defines the arguments for configuring a vector store table.
 */
export interface VectorStoreTableArgs {
  schemaName?: string;
  contentColumn?: string;
  embeddingColumn?: string;
  metadataColumns?: Column[];
  metadataJsonColumn?: string;
  idColumn?: string | Column;
  overwriteExisting?: boolean;
  storeMetadata?: boolean;
  concurrently?: boolean;
  indexName?: string;
}

/**
 * Represents a database table column.
 */
export class Column {
  name: string;
  dataType: string;
  nullable: boolean;

  /**
   * Creates an instance of Column.
   * @param {string} name - The name of the column.
   * @param {string} dataType - The data type of the column.
   * @param {boolean} [nullable=true] - Whether the column can be nullable. Defaults to true.
   */
  constructor(name: string, dataType: string, nullable: boolean = true) {
    this.name = name;
    this.dataType = dataType;
    this.nullable = nullable;

    this.postInitilization();
  }

  private postInitilization() {
    if (typeof this.name !== 'string') {
      throw 'Column name must be type string';
    }

    if (typeof this.dataType !== 'string') {
      throw 'Column data_type must be type string';
    }
  }
}

const USER_AGENT = 'genkit-cloud-sql-pg-js';

export class PostgresEngine {
  private static _createKey = Symbol();
  pool: knex.Knex<any, any[]>;
  static connector: Connector;

  constructor(key: Symbol, pool: knex.Knex<any, any[]>) {
    if (key !== PostgresEngine._createKey) {
      throw new Error("Only create class through 'create' method!");
    }
    this.pool = pool;
  }

  /**
   * @param projectId Required - GCP Project ID
   * @param region Required - Postgres Instance Region
   * @param instance Required - Postgres Instance name
   * @param database Required - Database name
   * @param ipType Optional - IP address type. Defaults to IPAddressType.PUBLIC
   * @param user Optional - Postgres user name. Defaults to undefined
   * @param password Optional - Postgres user password. Defaults to undefined
   * @param iamAccountEmail Optional - IAM service account email. Defaults to undefined
   * @returns PostgresEngine instance
   */

  static async fromInstance(
    projectId: string,
    region: string,
    instance: string,
    database: string,
    {
      ipType = IpAddressTypes.PUBLIC,
      user,
      password,
      iamAccountEmail,
    }: PostgresEngineArgs = {}
  ): Promise<PostgresEngine> {
    let dbUser: string;
    let enableIAMAuth: boolean;

    if ((!user && password) || (user && !password)) {
      // XOR for strings
      throw (
        "Only one of 'user' or 'password' were specified. Either " +
        'both should be specified to use basic user/password ' +
        'authentication or neither for IAM DB authentication.'
      );
    }

    // User and password are given so we use the basic auth
    if (user !== undefined && password !== undefined) {
      enableIAMAuth = false;
      dbUser = user!;
    } else {
      enableIAMAuth = true;
      if (iamAccountEmail !== undefined) {
        dbUser = iamAccountEmail;
      } else {
        // Get application default credentials
        const auth = new GoogleAuth({
          scopes: 'https://www.googleapis.com/auth/cloud-platform',
        });
        // dbUser should be the iam principal email by passing the credentials obtained
        dbUser = await getIAMPrincipalEmail(auth);
      }
    }

    PostgresEngine.connector = new Connector({ userAgent: USER_AGENT });
    const clientOpts = await PostgresEngine.connector.getOptions({
      instanceConnectionName: `${projectId}:${region}:${instance}`,
      ipType: ipType,
      authType: enableIAMAuth ? AuthTypes.IAM : AuthTypes.PASSWORD,
    });

    const dbConfig: knex.Knex.Config<any> = {
      client: 'pg',
      connection: {
        ...clientOpts,
        ...(password ? { password: password } : {}),
        user: dbUser,
        database: database,
      },
    };

    const engine = knex(dbConfig);

    return new PostgresEngine(PostgresEngine._createKey, engine);
  }

  /**
   * Create a PostgresEngine instance from an Knex instance.
   *
   * @param engine knex instance
   * @returns PostgresEngine instance from a knex instance
   */
  static async fromEngine(engine: knex.Knex<any, any[]>) {
    return new PostgresEngine(PostgresEngine._createKey, engine);
  }

  /**
   * Create a PostgresEngine instance from arguments.
   *
   * @param url URL use to connect to a database
   * @param poolConfig Optional - Configuration pool to use in the Knex configuration
   * @returns PostgresEngine instance
   */
  static async fromEngineArgs(
    url: string | knex.Knex.StaticConnectionConfig,
    poolConfig?: knex.Knex.PoolConfig
  ) {
    const driver = 'postgresql+asyncpg';

    if (typeof url === 'string' && !url.startsWith(driver)) {
      throw "Driver must be type 'postgresql+asyncpg'";
    }

    const dbConfig: knex.Knex.Config<any> = {
      client: 'pg',
      connection: url,
      acquireConnectionTimeout: 1000000,
      pool: {
        ...poolConfig,
        acquireTimeoutMillis: 600000,
      },
    };

    const engine = knex(dbConfig);

    return new PostgresEngine(PostgresEngine._createKey, engine);
  }

  /**
   * Create a table for saving of vectors to be used with PostgresVectorStore.
   *
   * @param tableName Postgres database table name
   * @param vectorSize Vector size for the embedding model to be used.
   * @param schemaName The schema name to store Postgres database table. Default: "public".
   * @param contentColumn Name of the column to store document content. Default: "content".
   * @param embeddingColumn Name of the column to store vector embeddings. Default: "embedding".
   * @param metadataColumns Optional - A list of Columns to create for custom metadata. Default: [].
   * @param metadataJsonColumn Optional - The column to store extra metadata in JSON format. Default: "json_metadata".
   * @param idColumn Optional - Column to store ids. Default: "id" column name with data type UUID.
   * @param overwriteExisting Whether to drop existing table. Default: False.
   * @param storeMetadata Whether to store metadata in the table. Default: True.
   */
  async initVectorstoreTable(
    tableName: string,
    vectorSize: number,
    {
      schemaName = 'public',
      contentColumn = 'content',
      embeddingColumn = 'embedding',
      metadataColumns = [],
      metadataJsonColumn = 'json_metadata',
      idColumn = 'id',
      overwriteExisting = false,
      storeMetadata = true,
    }: VectorStoreTableArgs = {}
  ): Promise<void> {
    await this.pool.raw('CREATE EXTENSION IF NOT EXISTS vector');

    if (overwriteExisting) {
      await this.pool.schema
        .withSchema(schemaName)
        .dropTableIfExists(tableName);
    }

    const idDataType =
      typeof idColumn === 'string' ? 'UUID' : idColumn.dataType;
    const idColumnName =
      typeof idColumn === 'string' ? idColumn : idColumn.name;

    let query = `CREATE TABLE "${schemaName}"."${tableName}"(
      ${idColumnName} ${idDataType} PRIMARY KEY,
      ${contentColumn} TEXT NOT NULL,
      ${embeddingColumn} vector(${vectorSize}) NOT NULL`;

    for (const column of metadataColumns) {
      const nullable = !column.nullable ? 'NOT NULL' : '';
      query += `,\n ${column.name} ${column.dataType} ${nullable}`;
    }

    if (storeMetadata) {
      query += `,\n${metadataJsonColumn} JSON`;
    }

    query += `\n);`;

    await this.pool.raw(query);
  }

  /**
   *  Dispose of connection pool
   */
  async closeConnection(): Promise<void> {
    await this.pool.destroy();
    if (PostgresEngine.connector !== undefined) {
      PostgresEngine.connector.close();
    }
  }

  /**
   * Just to test the connection to the database.
   * @returns A Promise that resolves to a row containing the current timestamp.
   */
  testConnection(): Promise<{ currentTimestamp: Date }[]> {
    return this.pool
      .raw<{ currentTimestamp: Date }[]>('SELECT NOW() as currentTimestamp')
      .then((result) => result.entries[0].currentTimestamp);
  }

  /**
   * Just to test the connection to the database and return the timestamp.
   * @returns A Promise that resolves to the current timestamp.
   */
  async getTestConnectionTimestamp(): Promise<Date> {
    const result = await this.pool.raw<{ currentTimestamp: Date }[]>(
      'SELECT NOW() as currentTimestamp'
    );
    return result.entries[0].currentTimestamp;
  }

  /**
   * Create an index on the vector store table
   * @param {string} tableName
   * @param {BaseIndex} index
   * @param {VectorStoreTableArgs}
   */
  async applyVectorIndex(
    tableName: string,
    index: BaseIndex,
    {
      schemaName = 'public',
      embeddingColumn = 'embedding',
      concurrently = false,
    }: VectorStoreTableArgs = {}
  ): Promise<void> {
    if (index instanceof ExactNearestNeighbor) {
      await this.dropVectorIndex({ tableName: tableName });
      return;
    }

    const filter = index.partialIndexes
      ? `WHERE (${index.partialIndexes})`
      : '';
    const indexOptions = `WITH ${index.indexOptions()}`;
    const funct = index.distanceStrategy.indexFunction;

    const name = index.name
      ? index.name
      : tableName + DEFAULT_INDEX_NAME_SUFFIX;

    const stmt = `CREATE INDEX ${concurrently ? 'CONCURRENTLY' : ''} ${name} ON "${schemaName}"."${tableName}" USING ${index.indexType} (${embeddingColumn} ${funct}) ${indexOptions} ${filter};`;

    await this.pool.raw(stmt);
  }

  /**
   * Check if index exists in the table.
   * @param {string} tableName
   * @param VectorStoreTableArgs Optional
   */
  async isValidIndex(
    tableName: string,
    { indexName, schemaName = 'public' }: VectorStoreTableArgs = {}
  ): Promise<boolean> {
    const idxName = indexName || tableName + DEFAULT_INDEX_NAME_SUFFIX;
    const stmt = `SELECT tablename, indexname
                          FROM pg_indexes
                          WHERE tablename = '${tableName}' AND schemaname = '${schemaName}' AND indexname = '${idxName}';`;
    const { rows } = await this.pool.raw(stmt);

    return rows.length === 1;
  }

  /**
   * Drop the vector index
   * @param {string} tableName
   * @param {string} indexName Optional - index name
   */
  async dropVectorIndex(params: {
    tableName?: string;
    indexName?: string;
  }): Promise<void> {
    let idxName = '';
    if (params.indexName) {
      idxName = params.indexName;
    } else if (params.tableName) {
      idxName = params.tableName + DEFAULT_INDEX_NAME_SUFFIX;
    } else {
      throw new Error('Index name or Table name are not provided.');
    }
    const query = `DROP INDEX IF EXISTS ${idxName};`;
    await this.pool.raw(query);
  }

  /**
   * Re-index the vector store table
   * @param {string} tableName
   * @param {string} indexName Optional - index name
   */
  async reIndex(params: { tableName?: string; indexName?: string }) {
    let idxName = '';
    if (params.indexName) {
      idxName = params.indexName;
    } else if (params.tableName) {
      idxName = params.tableName + DEFAULT_INDEX_NAME_SUFFIX;
    } else {
      throw new Error('Index name or Table name are not provided.');
    }
    const query = `REINDEX INDEX ${idxName};`;
    this.pool.raw(query);
  }
}
