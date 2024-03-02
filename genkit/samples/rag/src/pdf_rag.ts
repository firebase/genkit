import { prompt, promptTemplate } from '@google-genkit/ai';
import { generate } from '@google-genkit/ai/generate';
import { TextDocument, index, retrieve } from '@google-genkit/ai/retrievers';
import { flow, run } from '@google-genkit/flow';
import { geminiPro } from '@google-genkit/plugin-vertex-ai';
import {
  pineconeIndexerRef,
  pineconeRetrieverRef,
} from '@google-genkit/providers/pinecone';
import { chunk } from 'llm-chunk';
import path from 'path';
import * as z from 'zod';

export const pdfChatRetriever = pineconeRetrieverRef({
  indexId: 'pdf-chat',
  displayName: 'PDF Chat',
});
export const pdfChatIndexer = pineconeIndexerRef({
  indexId: 'pdf-chat',
  displayName: 'PDF Chat',
});

const ragTemplate = `Use the following pieces of context to answer the question at the end.
 If you don't know the answer, just say that you don't know, don't try to make up an answer.
 
{context}
Question: {question}
Helpful Answer:`;

// Define a simple RAG flow, we will evaluate this flow
export const pdfQA = flow(
  {
    name: 'pdfQA',
    input: z.string(),
    output: z.string(),
  },
  async (query) => {
    const docs = await retrieve({
      retriever: pdfChatRetriever,
      query,
      options: { k: 3 },
    });
    console.log(docs);

    const augmentedPrompt = await promptTemplate({
      template: prompt(ragTemplate),
      variables: {
        question: query,
        context: docs.map((d) => d.content).join('\n\n'),
      },
    });
    const llmResponse = await generate({
      model: geminiPro,
      prompt: { text: augmentedPrompt.prompt },
    });
    return llmResponse.text();
  }
);

const chunkingConfig = {
  minLength: 1000, // number of minimum characters into chunk
  maxLength: 2000, // number of maximum characters into chunk
  splitter: 'sentence', // paragraph | sentence
  overlap: 100, // number of overlap chracters
  delimiters: '', // regex for base split method
} as any;

// Define a flow to index documents into the "vector store"
export const indexPdf = flow(
  {
    name: 'indexPdf',
    input: z.string().describe('PDF file path'),
    output: z.void(),
  },
  async (filePath) => {
    filePath = path.resolve(filePath);
    const pdfTxt = await run('extract-text', () => extractText(filePath));

    const chunks = await run('chunk-it', async () =>
      chunk(pdfTxt, chunkingConfig)
    );

    const transformedDocs: TextDocument[] = chunks.map((text) => {
      return { content: text, metadata: { filePath } };
    });

    await index({
      indexer: pdfChatIndexer,
      docs: transformedDocs,
      options: {
        namespace: '',
      },
    });
  }
);

async function extractText(filePath: string): Promise<string> {
  const pdfjsLib = await import('pdfjs-dist');
  let doc = await pdfjsLib.getDocument(filePath).promise;

  var pdfTxt = '';
  const numPages = doc.numPages;
  for (var i = 1; i <= numPages; i++) {
    let page = await doc.getPage(i);
    let content = await page.getTextContent();
    let strings = content.items.map((item) => {
      const str: string = (item as any).str;
      return str === '' ? '\n' : str;
    });

    pdfTxt += '\n\npage ' + i + '\n\n' + strings.join('');
  }
  return pdfTxt;
}

// genkit flow:run synthesizeQuestions '"35650.pdf"' --output synthesizedQuestions.json
export const synthesizeQuestions = flow(
  {
    name: 'synthesizeQuestions',
    input: z.string().describe('PDF file path'),
    output: z.array(z.string()),
  },
  async (filePath) => {
    filePath = path.resolve(filePath);
    const pdfTxt = await run('extract-text', () => extractText(filePath));

    const chunks = await run('chunk-it', async () =>
      chunk(pdfTxt, chunkingConfig)
    );

    const questions: string[] = [];
    for (var i = 0; i < chunks.length; i++) {
      const qResponse = await generate({
        model: geminiPro,
        prompt: {
          text: `Generate one question about the text below: ${chunks[i]}`,
        },
      });
      questions.push(qResponse.text());
    }
    return questions;
  }
);
