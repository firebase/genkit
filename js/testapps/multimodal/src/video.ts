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

import {
  devLocalIndexerRef,
  devLocalRetrieverRef,
} from '@genkit-ai/dev-local-vectorstore';
import fileTypeChecker from 'file-type-checker';
import fs from 'fs';
import { Document, z } from 'genkit';
import { chromaIndexerRef, chromaRetrieverRef } from 'genkitx-chromadb';
import { pineconeIndexerRef, pineconeRetrieverRef } from 'genkitx-pinecone';
import path from 'path';

import { ai } from './genkit.js';
import { augmentedVideoPrompt } from './prompt.js';

export const localVideoRetriever = devLocalRetrieverRef('localMultiModalIndex');
export const localVideoIndexer = devLocalIndexerRef('localMultiModalIndex');

// Before using this, set up a pinecone database with
// dimension: 1408 and metric: cosine.
// Also set the PINECONE_API_KEY environment variable with your key.
export const pineconeVideoRetriever = pineconeRetrieverRef({
  indexId: 'pinecone-multimodal-index',
  displayName: 'Pinecone video retriever',
});

export const pineconeVideoIndexer = pineconeIndexerRef({
  indexId: 'pinecone-multimodal-index',
  displayName: 'Pinecone video indexer',
});

export const chromaVideoRetriever = chromaRetrieverRef({
  collectionName: 'multimodal_collection',
  displayName: 'Chroma Video retriever',
});

export const chromaVideoIndexer = chromaIndexerRef({
  collectionName: 'multimodal_collection',
  displayName: 'Chroma video indexer',
});

// Define a local video indexer flow
export const localIndexVideo = ai.defineFlow(
  {
    name: 'localIndexVideo',
    inputSchema: z
      .string()
      .describe('A Video URL')
      .default('gs://cloud-samples-data/generative-ai/video/pixel8.mp4'),
  },
  async (videoUrl: string) => {
    const documents = await ai.run('extract-video', () =>
      extractVideo(videoUrl)
    );

    await ai.index({
      indexer: localVideoIndexer,
      documents,
    });
  }
);

// Define a pinecone video indexer flow
export const pineconeIndexVideo = ai.defineFlow(
  {
    name: 'pineconeIndexVideo',
    inputSchema: z
      .string()
      .describe('A Video URL')
      .default('gs://cloud-samples-data/generative-ai/video/pixel8.mp4'),
  },
  async (videoUrl: string) => {
    const documents = await ai.run('extract-video', () =>
      extractVideo(videoUrl)
    );

    await ai.index({
      indexer: pineconeVideoIndexer,
      documents,
    });
  }
);

// Define a chroma video indexer flow
export const chromaIndexVideo = ai.defineFlow(
  {
    name: 'chromaIndexVideo',
    inputSchema: z
      .string()
      .describe('A Video URL')
      .default('gs://cloud-samples-data/generative-ai/video/pixel8.mp4'),
  },
  async (videoUrl: string) => {
    const documents = await ai.run('extract-video', () =>
      extractVideo(videoUrl)
    );

    await ai.index({
      indexer: chromaVideoIndexer,
      documents,
    });
  }
);

// Suffix based type
function getVideoType(url: string) {
  const lastDotIndex = url.lastIndexOf('.');
  if (lastDotIndex === -1) {
    throw new Error('Error: Unable to determine video mime type');
  }
  const suffix = url.substring(lastDotIndex + 1);
  return `video/${suffix}`;
}

async function extractVideo(filePath: string): Promise<Document[]> {
  const videoDocs: Document[] = [];

  if (filePath.startsWith('http')) {
    throw new Error(
      'Vertex AI does not support http(s) video urls. Please use Google Cloud Storage (gs://) urls'
    );
  } else if (filePath.startsWith('gs://')) {
    // The default configuration is to look at the first 120 seconds of the
    // video and produce embeddings in 16 second increments.
    // This is not really necessary, since we are very close to the defaults
    // (i.e. 15 v.s. 16 seconds) it is just here to show what it looks like.
    // See also:
    // https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-multimodal-embeddings#video-modes
    // for pricing differences for the different intervals.
    const metadataFirst120Seconds = {
      videoSegmentConfig: {
        startOffsetSec: 0,
        endOffsetSec: 120,
        intervalSec: 15,
      },
    };

    // If your video is longer than 120 seconds, you can add additional video
    // document requests with different start/stop values e.g.
    // const metadataNext120Seconds = {
    //   "videoSegmentConfig": {
    //     "startOffsetSec": 120,
    //     "endOffsetSec": 240,
    //     "intervalSec": 15
    //   }
    // }
    // and then:
    // videoDocs.push(Document.fromMedia(filePath, getVideoType(filePath), metadataNext120Seconds));
    //
    // sample ~4 minute video: gs://cloud-samples-data/generative-ai/video/google_sustainability.mp4

    videoDocs.push(
      Document.fromMedia(
        filePath,
        getVideoType(filePath),
        metadataFirst120Seconds
      )
    );

    return videoDocs;
  }

  // Note, this is valid, but it only works for very very tiny videos.
  // Otherwise the API request message size is too big.
  // The recommended way to handle video is using a 'gs://' URL
  const file = path.resolve(filePath);
  const dataBuffer = fs.readFileSync(file);
  const detectedFileInfo = fileTypeChecker.detectFile(dataBuffer);
  if (
    detectedFileInfo?.mimeType &&
    detectedFileInfo?.mimeType.startsWith('video/')
  ) {
    videoDocs.push(
      Document.fromMedia(
        dataBuffer.toString('base64'),
        detectedFileInfo?.mimeType
      )
    );
  } else {
    throw new Error('Error: Unable to determine mime type of the file.');
  }
  return videoDocs;
}

// Define a video QA flow
export const localVideoQAFlow = ai.defineFlow(
  {
    name: 'localVideoQuestions',
    inputSchema: z
      .string()
      .describe('A question about the video')
      .default('describe the video'),
    outputSchema: z.string(),
  },
  async (query: string, { sendChunk }) => {
    const docs = (await ai.retrieve({
      retriever: localVideoRetriever,
      query,
      options: { k: 1 }, // we are choosing a single segment of video for context
    })) as Document[];

    return augmentedVideoPrompt(
      {
        question: query,
        media: docs
          .filter(
            (d) => d.media[0]?.url?.length && d.media[0]?.contentType?.length
          )
          .map((d) => {
            console.log(
              `Retriever returned video: ${d.media[0].url} from ${d.metadata?.embedMetadata?.startOffsetSec}s to ${d.metadata?.embedMetadata?.endOffsetSec}s`
            );
            return {
              gcsUrl: d.media[0]?.url,
              contentType: d.media[0]?.contentType || '',
              startOffsetSec: d.metadata?.embedMetadata
                ?.startOffsetSec as number,
              endOffsetSec: d.metadata?.embedMetadata?.endOffsetSec as number,
            };
          })[0],
      },
      {
        onChunk: (c) => sendChunk(c.text),
      }
    ).then((r) => r.text);
  }
);

// Define a video QA flow
export const pineconeVideoQAFlow = ai.defineFlow(
  {
    name: 'pineconeVideoQuestions',
    inputSchema: z
      .string()
      .describe('A question about the video')
      .default('describe the video'),
    outputSchema: z.string(),
  },
  async (query: string, { sendChunk }) => {
    const docs = (await ai.retrieve({
      retriever: pineconeVideoRetriever,
      query,
      options: { k: 1 }, // we are choosing a single segment of video for context
    })) as Document[];

    return augmentedVideoPrompt(
      {
        question: query,
        media: docs
          .filter(
            (d) => d.media[0]?.url?.length && d.media[0]?.contentType?.length
          )
          .map((d) => {
            console.log(
              `Retriever returned video: ${d.media[0].url} from ${d.metadata?.embedMetadata?.startOffsetSec}s to ${d.metadata?.embedMetadata?.endOffsetSec}s`
            );
            return {
              gcsUrl: d.media[0]?.url,
              contentType: d.media[0]?.contentType || '',
              startOffsetSec: d.metadata?.embedMetadata
                ?.startOffsetSec as number,
              endOffsetSec: d.metadata?.embedMetadata?.endOffsetSec as number,
            };
          })[0],
      },
      {
        onChunk: (c) => sendChunk(c.text),
      }
    ).then((r) => r.text);
  }
);

export const chromaVideoQAFlow = ai.defineFlow(
  {
    name: 'chromaVideoQuestions',
    inputSchema: z
      .string()
      .describe('A question about the video')
      .default('describe the video'),
    outputSchema: z.string(),
  },
  async (query: string, { sendChunk }) => {
    const docs = (await ai.retrieve({
      retriever: chromaVideoRetriever,
      query,
      options: { k: 1 }, // we are choosing a single segment of video for context
    })) as Document[];

    return augmentedVideoPrompt(
      {
        question: query,
        media: docs
          .filter(
            (d) => d.media[0]?.url?.length && d.media[0]?.contentType?.length
          )
          .map((d) => {
            console.log(
              `Retriever returned video: ${d.media[0].url} from ${d.metadata?.embedMetadata?.startOffsetSec}s to ${d.metadata?.embedMetadata?.endOffsetSec}s`
            );
            return {
              gcsUrl: d.media[0]?.url,
              contentType: d.media[0]?.contentType || '',
              startOffsetSec: d.metadata?.embedMetadata
                ?.startOffsetSec as number,
              endOffsetSec: d.metadata?.embedMetadata?.endOffsetSec as number,
            };
          })[0],
      },
      {
        onChunk: (c) => sendChunk(c.text),
      }
    ).then((r) => r.text);
  }
);
