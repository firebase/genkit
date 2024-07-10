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
	//!+vec
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
	//!-vec
	//!+splitcfg
	splitter := textsplitter.NewRecursiveCharacter(
		textsplitter.WithChunkSize(200),
		textsplitter.WithChunkOverlap(20),
	)
	//!-splitcfg
	//!+indexflow
	genkit.DefineFlow(
		"indexMenu",
		func(ctx context.Context, path string) (any, error) {
			// Extract plain text from the PDF. Wrap the logic in Tun so it
			// appears as a step in your traces.
			pdfText, err := genkit.Run(ctx, "extract", func() (string, error) {
				return readPDF(path)
			})
			if err != nil {
				return nil, err
			}

			// Split the text into chunks. Wrap the logic in Tun so it
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
	//!-indexflow

	err = genkit.Init(ctx, nil)
	if err != nil {
		log.Fatal(err)
	}
}

// !+readpdf
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

	var buf []byte
	_, err = reader.Read(buf)
	return string(buf), err
}

//!-readpdf

func menuQA() {
	//!+retrieve
	ctx := context.Background()

	err := vertexai.Init(ctx, &vertexai.Config{})
	if err != nil {
		log.Fatal(err)
	}
	err = localvec.Init()
	if err != nil {
		log.Fatal(err)
	}

	model := vertexai.Model("gemini-1.5-pro")

	_, menuPdfRetriever, err := localvec.DefineIndexerAndRetriever(
		"menuQA",
		localvec.Config{
			Embedder: vertexai.Embedder("text-embedding-004"),
		},
	)

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
			resp, err := model.Generate(ctx, &ai.GenerateRequest{
				Messages: []*ai.Message{
					ai.NewSystemTextMessage(`
You are acting as a helpful AI assistant that can answer questions about the
food available on the menu at Genkit Grub Pub.
Use only the context provided to answer the question. If you don't know, do not
make up an answer. Do not add or change items on the menu.`),
					menuInfo,
					ai.NewUserTextMessage(question),
				},
			}, nil)
			if err != nil {
				return "", err
			}

			return resp.Text()
		})
	//!-retrieve
}

func customret() {
	_, menuPDFRetriever, _ := localvec.DefineIndexerAndRetriever(
		"menuQA",
		localvec.Config{
			Embedder: vertexai.Embedder("text-embedding-004"),
		},
	)

	//!+customret
	type CustomMenuRetrieverOptions struct {
		K          int
		PreRerankK int
	}
	advancedMenuRetriever := ai.DefineRetriever(
		"custom",
		"advancedMenuRetriever",
		func(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
			// Handle options passed using our custom type.
			k := 3
			preRerankK := 10
			if opts, ok := req.Options.(CustomMenuRetrieverOptions); ok {
				k = opts.K
				preRerankK = opts.PreRerankK
			}

			// Call the retriever as in the simple case.
			response, err := menuPDFRetriever.Retrieve(ctx, &ai.RetrieverRequest{
				Document: req.Document,
				Options:  localvec.RetrieverOptions{K: preRerankK},
			})
			if err != nil {
				return nil, err
			}

			// Re-rank the returned documents using your custom function.
			rerankedDocs := rerank(response.Documents)
			response.Documents = rerankedDocs[:k]

			return response, nil
		},
	)
	//!-customret

	_ = advancedMenuRetriever
}

func rerank(document []*ai.Document) []*ai.Document {
	panic("unimplemented")
}
