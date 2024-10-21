import devLocalVectorstore, {
  devLocalIndexerRef,
  devLocalRetrieverRef,
} from '@genkit-ai/dev-local-vectorstore';
import { textEmbedding004, vertexAI } from '@genkit-ai/vertexai';
import { genkit } from 'genkit';
import { readFileSync } from 'node:fs';

const ai = genkit({
  plugins: [
    vertexAI({ projectId: 'bleigh-genkit-test', location: 'us-central1' }),
    devLocalVectorstore([
      { indexName: 'school-handbook', embedder: textEmbedding004 },
    ]),
  ],
});

const indexer = devLocalIndexerRef('school-handbook');

async function makeEmbeddings() {
  const policies = readFileSync('./src/handbook.txt', {
    encoding: 'utf8',
  }).split(/\n\n/);

  await ai.index({
    indexer,
    documents: policies.map((p) => ({ content: [{ text: p }] })),
  });
}

const retriever = devLocalRetrieverRef('school-handbook');

async function testRetrieval() {
  console.log(
    (
      await ai.retrieve({
        retriever,
        query: "What's the dress code?",
        options: { n: 3 },
      })
    ).map((d) => d.text)
  );
}

testRetrieval();
