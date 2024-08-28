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

import { embed, EmbedderArgument } from '@genkit-ai/ai/embedder';
import {
  defineRetriever,
  DocumentData,
  Part,
  RetrieverAction,
} from '@genkit-ai/ai/retriever';
import {
  Firestore,
  Query,
  QueryDocumentSnapshot,
  VectorQuerySnapshot,
} from '@google-cloud/firestore';
import z from 'zod';

function toContent(
  d: QueryDocumentSnapshot,
  contentField: string | ((snap: QueryDocumentSnapshot) => Part[])
): Part[] {
  if (typeof contentField === 'function') {
    return contentField(d);
  }

  return [{ text: d.get(contentField) }];
}

function toDocuments(
  result: VectorQuerySnapshot,
  vectorField: string,
  contentField: string | ((snap: QueryDocumentSnapshot) => Part[]),
  metadataFields?:
    | string[]
    | ((snap: QueryDocumentSnapshot) => Record<string, any>)
): DocumentData[] {
  return result.docs.map((d) => {
    const out: DocumentData = { content: toContent(d, contentField) };
    if (typeof metadataFields === 'function') {
      out.metadata = metadataFields(d);
      return out;
    }

    out.metadata = { id: d.id };
    if (metadataFields) {
      for (const field of metadataFields) {
        out.metadata[field] = d.get(field);
      }
      return out;
    }

    out.metadata = d.data();
    delete out.metadata[vectorField];
    if (typeof contentField === 'string') delete out.metadata[contentField];
    return out;
  });
}

/**
 * Define a retriever that uses vector similarity search to retrieve documents from Firestore.
 * You must create a vector index on the associated field before you can perform nearest-neighbor
 * search.
 **/
export function defineFirestoreRetriever(config: {
  /** The name of the retriever. */
  name: string;
  /** Optional label for display in Developer UI. */
  label?: string;
  /** The Firestore database instance from which to query. */
  firestore: Firestore;
  /** The name of the collection from which to query. */
  collection?: string;
  /** The embedder to use with this retriever. */
  embedder: EmbedderArgument;
  /** The name of the field within the collection containing the vector data. */
  vectorField: string;
  /** The name of the field containing the document content you wish to return. */
  contentField: string | ((snap: QueryDocumentSnapshot) => Part[]);
  /** The distance measure to use when comparing vectors. Defaults to 'COSINE'. */
  distanceMeasure?: 'EUCLIDEAN' | 'COSINE' | 'DOT_PRODUCT';
  /**
   * A list of fields to include in the returned document metadata. If not supplied, all fields other
   * than the vector are included. Alternatively, provide a transform function to extract the desired
   * metadata fields from a snapshot.
   **/
  metadataFields?:
    | string[]
    | ((snap: QueryDocumentSnapshot) => Record<string, any>);
}): RetrieverAction {
  const {
    name,
    label,
    firestore,
    embedder,
    collection,
    vectorField,
    metadataFields,
    contentField,
    distanceMeasure,
  } = config;
  return defineRetriever(
    {
      name,
      info: {
        label: label || `Firestore - ${name}`,
      },
      configSchema: z.object({
        where: z.record(z.any()).optional(),
        limit: z.number(),
        /* Supply or override the collection for retrieval. */
        collection: z.string().optional(),
      }),
    },
    async (input, options) => {
      const embedding = await embed({ embedder, content: input });
      if (!options.collection && !collection) {
        throw new Error(
          'Must specify a collection to query in Firestore retriever.'
        );
      }
      let query: Query = firestore.collection(
        options.collection || collection!
      );
      for (const field in options.where || {}) {
        query = query.where(field, '==', options.where![field]);
      }
      const result = await query
        .findNearest(vectorField, embedding, {
          limit: options.limit || 10,
          distanceMeasure: distanceMeasure || 'COSINE',
        })
        .get();

      return {
        documents: toDocuments(
          result,
          vectorField,
          contentField,
          metadataFields
        ),
      };
    }
  );
}
