// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package rag

import (
	"context"
	"io"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/localvec"
	"github.com/firebase/genkit/go/plugins/vertexai"

	// "github.com/ledongthuc/pdf"
	// "github.com/tmc/langchaingo/textsplitter"
	"github.com/firebase/genkit/go/internal/doc-snippets/rag/pdf"
	"github.com/firebase/genkit/go/internal/doc-snippets/rag/textsplitter"
)

func main() {
	// [START vec]
	ctx := context.Background()

	err := vertexai.Init(ctx, &vertexai.Config{})
	if err != nil {
		log.Fatal(err)
	}
	err = localvec.Init()
	if err != nil {
		log.Fatal(err)
	}

	menuPDFIndexer, _, err := localvec.DefineIndexerAndRetriever(
		"menuQA",
		localvec.Config{
			Embedder: vertexai.Embedder("text-embedding-004"),
		},
	)
	if err != nil {
		log.Fatal(err)
	}
	// [END vec]
	// [START splitcfg]
	splitter := textsplitter.NewRecursiveCharacter(
		textsplitter.WithChunkSize(200),
		textsplitter.WithChunkOverlap(20),
	)
	// [END splitcfg]
	// [START indexflow]
	genkit.DefineFlow(
		"indexMenu",
		func(ctx context.Context, path string) (any, error) {
			// Extract plain text from the PDF. Wrap the logic in Run so it
			// appears as a step in your traces.
			pdfText, err := genkit.Run(ctx, "extract", func() (string, error) {
				return readPDF(path)
			})
			if err != nil {
				return nil, err
			}

			// Split the text into chunks. Wrap the logic in Run so it
			// appears as a step in your traces.
			docs, err := genkit.Run(ctx, "chunk", func() ([]*ai.Document, error) {
				chunks, err := splitter.SplitText(pdfText)
				if err != nil {
					return nil, err
				}

				var docs []*ai.Document
				for _, chunk := range chunks {
					docs = append(docs, ai.DocumentFromText(chunk, nil))
				}
				return docs, nil
			})
			if err != nil {
				return nil, err
			}

			// Add chunks to the index.
			err = menuPDFIndexer.Index(ctx, &ai.IndexerRequest{Documents: docs})
			return nil, err
		},
	)
	// [END indexflow]

	err = genkit.Init(ctx, nil)
	if err != nil {
		log.Fatal(err)
	}
}

// [START readpdf]
// Helper function to extract plain text from a PDF. Excerpted from
// https://github.com/ledongthuc/pdf
func readPDF(path string) (string, error) {
	f, r, err := pdf.Open(path)
	if f != nil {
		defer f.Close()
	}
	if err != nil {
		return "", err
	}

	reader, err := r.GetPlainText()
	if err != nil {
		return "", err
	}

	bytes, err := io.ReadAll(reader)
	if err != nil {
		return "", err
	}
	return string(bytes), nil
}

// [END readpdf]

func menuQA() {
	// [START retrieve]
	ctx := context.Background()

	err := vertexai.Init(ctx, &vertexai.Config{})
	if err != nil {
		log.Fatal(err)
	}
	err = localvec.Init()
	if err != nil {
		log.Fatal(err)
	}

	model := vertexai.Model("gemini-1.5-flash")

	_, menuPdfRetriever, err := localvec.DefineIndexerAndRetriever(
		"menuQA",
		localvec.Config{
			Embedder: vertexai.Embedder("text-embedding-004"),
		},
	)
	if err != nil {
		log.Fatal(err)
	}

	genkit.DefineFlow(
		"menuQA",
		func(ctx context.Context, question string) (string, error) {
			// Retrieve text relevant to the user's question.
			docs, err := menuPdfRetriever.Retrieve(ctx, &ai.RetrieverRequest{
				Document: ai.DocumentFromText(question, nil),
			})
			if err != nil {
				return "", err
			}

			// Construct a system message containing the menu excerpts you just
			// retrieved.
			menuInfo := ai.NewSystemTextMessage("Here's the menu context:")
			for _, doc := range docs.Documents {
				menuInfo.Content = append(menuInfo.Content, doc.Content...)
			}

			// Call Generate, including the menu information in your prompt.
			return ai.GenerateText(ctx, model,
				ai.WithMessages(
					ai.NewSystemTextMessage(`
You are acting as a helpful AI assistant that can answer questions about the
food available on the menu at Genkit Grub Pub.
Use only the context provided to answer the question. If you don't know, do not
make up an answer. Do not add or change items on the menu.`),
					menuInfo,
					ai.NewUserTextMessage(question)))
		})
	// [END retrieve]
}

func customret() {
	_, menuPDFRetriever, _ := localvec.DefineIndexerAndRetriever(
		"menuQA",
		localvec.Config{
			Embedder: vertexai.Embedder("text-embedding-004"),
		},
	)

	// [START customret]
	type CustomMenuRetrieverOptions struct {
		K          int
		PreRerankK int
	}
	advancedMenuRetriever := ai.DefineRetriever(
		"custom",
		"advancedMenuRetriever",
		func(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
			// Handle options passed using our custom type.
			opts, _ := req.Options.(CustomMenuRetrieverOptions)
			// Set fields to default values when either the field was undefined
			// or when req.Options is not a CustomMenuRetrieverOptions.
			if opts.K == 0 {
				opts.K = 3
			}
			if opts.PreRerankK == 0 {
				opts.PreRerankK = 10
			}

			// Call the retriever as in the simple case.
			response, err := menuPDFRetriever.Retrieve(ctx, &ai.RetrieverRequest{
				Document: req.Document,
				Options:  localvec.RetrieverOptions{K: opts.PreRerankK},
			})
			if err != nil {
				return nil, err
			}

			// Re-rank the returned documents using your custom function.
			rerankedDocs := rerank(response.Documents)
			response.Documents = rerankedDocs[:opts.K]

			return response, nil
		},
	)
	// [END customret]

	_ = advancedMenuRetriever
}

func rerank(document []*ai.Document) []*ai.Document {
	panic("unimplemented")
}
