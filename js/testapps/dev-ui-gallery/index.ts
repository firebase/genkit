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
import { googleAI } from '@genkit-ai/googleai';
import { genkit } from 'genkit';
import { Document } from 'genkit/retriever';
import { mongodb } from 'genkitx-mongodb';

const ai = genkit({
  plugins: [
    googleAI(),
    mongodb([
      {},
      //   {
      //     uri: process.env.MONGODB_URI!,
      //     dbName: 'genkit',
      //     collection: 'vector_test',
      //     vectorField: 'summary',
      //     embedder: textEmbeddingAda002,
      //     //similarityMetric: 'dotProduct',
      //     retry: {
      //       indexing: 3,
      //       search: 2,
      //     },
      //   },
    ]),
  ],
});

const indexer = mongodbIndexerRef({ name: 'vector_test' });

async function main() {
  await ai.index({
    indexer,
    documents: [
      Document.fromText(
        'The space shuttle launched successfully from Cape Canaveral.',
        { id: 'doc1' }
      ),
      // Document.fromText('A delicious recipe for making vegan lasagna at home.', { id: 'doc2' }),
      // Document.fromText('A brief history of the Apollo moon missions.', { id: 'doc3' }),
      // Document.fromText('Climate change is accelerating due to greenhouse gas emissions.', { id: 'doc4' }),
      // Document.fromText('The Great Wall of China stretches over 13,000 miles and was built over centuries.', { id: 'doc5' }),
      // Document.fromText('Apple announced new features for iOS 18 at the annual developer conference.', { id: 'doc6' }),
      // Document.fromText('The Amazon rainforest is home to over 3 million species of plants and animals.', { id: 'doc7' }),
      // Document.fromText('A beginner’s guide to investing in mutual funds and ETFs.', { id: 'doc8' }),
      // Document.fromText('Top 10 destinations to visit in Europe during spring.', { id: 'doc9' }),
      // Document.fromText('Understanding the basics of machine learning and neural networks.', { id: 'doc10' }),
      // Document.fromText('The human brain has around 86 billion neurons.', { id: 'doc11' }),
      // Document.fromText('The World Health Organization declared the end of the global pandemic emergency.', { id: 'doc12' }),
      // Document.fromText('Mount Everest is the tallest mountain on Earth at 8,848 meters above sea level.', { id: 'doc13' }),
      // Document.fromText('A healthy breakfast includes protein, fiber, and complex carbohydrates.', { id: 'doc14' }),
      // Document.fromText('The Python programming language is popular for data science and automation.', { id: 'doc15' }),
    ],
  });

  console.log('✅ Documents indexed successfully!');
}

main().catch(console.error);
