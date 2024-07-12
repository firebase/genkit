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

import { Document, DocumentDataSchema } from '@genkit-ai/ai/retriever';
import { BigQuery } from '@google-cloud/bigquery';
import { DocumentIndexer, DocumentRetriever, Neighbor } from './types';
/**
 * Creates a BigQuery Document Retriever.
 *
 * This function returns a DocumentRetriever function that retrieves documents
 * from a BigQuery table based on the provided neighbors.
 *
 * @param {BigQuery} bq - The BigQuery instance.
 * @param {string} tableId - The ID of the BigQuery table.
 * @param {string} datasetId - The ID of the BigQuery dataset.
 * @returns {DocumentRetriever} - The DocumentRetriever function.
 */
export const getBigQueryDocumentRetriever = (
  bq: BigQuery,
  tableId: string,
  datasetId: string
): DocumentRetriever => {
  const bigQueryRetriever: DocumentRetriever = async (
    neighbors: Neighbor[]
  ): Promise<Document[]> => {
    const ids = neighbors
      .map((neighbor) => neighbor.datapoint?.datapointId)
      .filter(Boolean);
    const query = `
      SELECT * FROM \`${datasetId}.${tableId}\`
      WHERE id IN UNNEST(@ids)
    `;
    const options = {
      query,
      params: { ids },
    };
    const [rows] = await bq.query(options);
    const docs: (Document | null)[] = rows
      .map((row) => {
        const docData = {
          content: JSON.parse(row.content),
          metadata: {
            ...neighbors.find(
              (neighbor) => neighbor.datapoint?.datapointId === row.id
            ),
          },
        };
        const parsedDocData = DocumentDataSchema.safeParse(docData);
        if (parsedDocData.success) {
          return new Document(parsedDocData.data);
        }
        return null;
      })
      .filter((doc) => doc !== null) as Document[];
    return docs as Document[];
  };
  return bigQueryRetriever;
};

/**
 * Creates a BigQuery Document Indexer.
 *
 * This function returns a DocumentIndexer function that indexes documents
 * into a BigQuery table.
 *
 * @param {BigQuery} bq - The BigQuery instance.
 * @param {string} tableId - The ID of the BigQuery table.
 * @param {string} datasetId - The ID of the BigQuery dataset.
 * @returns {DocumentIndexer} - The DocumentIndexer function.
 */
export const getBigQueryDocumentIndexer = (
  bq: BigQuery,
  tableId: string,
  datasetId: string
): DocumentIndexer => {
  const bigQueryIndexer: DocumentIndexer = async (
    docs: Document[]
  ): Promise<string[]> => {
    const ids: string[] = [];
    const rows = docs.map((doc) => {
      const id = Math.random().toString(36).substring(7);
      ids.push(id);
      return {
        id,
        content: JSON.stringify(doc.content),
        metadata: JSON.stringify(doc.metadata),
      };
    });
    await bq.dataset(datasetId).table(tableId).insert(rows);
    return ids;
  };
  return bigQueryIndexer;
};
