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

package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/localvec"
	"github.com/firebase/genkit/go/plugins/vertexai"
	"github.com/invopop/jsonschema"
)

const (
	geminiPro      = "gemini-1.0-pro"
	embeddingGecko = "textembedding-gecko"
)

// menuItem is the data model for an item on the menu.
type menuItem struct {
	Title       string  `json:"title" jsonschema_description:"The name of the menu item"`
	Description string  `json:"description" jsonschema_description:"Details including ingredients and preparation"`
	Price       float64 `json:"price" jsonschema_description:"Price in dollars"`
}

// menuQuestionInput is a question about the menu.
type menuQuestionInput struct {
	Question string `json:"question"`
}

// menuQuestionInputSchema is the JSON schema for a menuQuestionInput.
var menuQuestionInputSchema = jsonschema.Reflect(menuQuestionInput{})

// answerOutput is an answer to a question.
type answerOutput struct {
	Answer string `json:"answer"`
}

// dataMenuQuestionInput is a question about the menu,
// where the menu is provided in the JSON data.
type dataMenuQuestionInput struct {
	MenuData []*menuItem `json:"menuData"`
	Question string      `json:"question"`
}

// dataMenuQuestionInputSchema is the JSON schema for a dataMenuQuestionInput.
var dataMenuQuestionInputSchema = jsonschema.Reflect(dataMenuQuestionInput{})

// textMenuQuestionInput is for a question about the menu,
// where the menu is provided as unstructured text.
type textMenuQuestionInput struct {
	MenuText string `json:"menuText"`
	Question string `json:"question"`
}

// textMenuQuestionInputSchema is the JSON schema for a textMenuQuestionInput.
var textMenuQuestionInputSchema = jsonschema.Reflect(textMenuQuestionInput{})

func main() {
	projectID := os.Getenv("GCLOUD_PROJECT")
	if projectID == "" {
		fmt.Fprintln(os.Stderr, "menu example requires setting GCLOUD_PROJECT in the environment.")
		os.Exit(1)
	}

	ctx := context.Background()
	err := vertexai.Init(ctx, vertexai.Config{
		ProjectID: projectID,
		Location:  os.Getenv("GCLOUD_LOCATION"),
		Models:    []string{geminiPro, geminiPro + "-vision"},
		Embedders: []string{embeddingGecko},
	})
	if err != nil {
		log.Fatal(err)
	}
	model := vertexai.Model(geminiPro)
	if err := setup01(ctx, model); err != nil {
		log.Fatal(err)
	}
	if err := setup02(ctx, model); err != nil {
		log.Fatal(err)
	}

	if err := setup03(ctx, model); err != nil {
		log.Fatal(err)
	}

	indexer, retriever, err := localvec.Init(ctx, localvec.Config{
		Name:     "go-menu-items",
		Embedder: vertexai.Embedder(embeddingGecko),
	})
	if err != nil {
		log.Fatal(err)
	}
	if err := setup04(ctx, indexer, retriever, model); err != nil {
		log.Fatal(err)
	}

	if err := setup05(ctx, model, vertexai.Model(geminiPro+"-vision")); err != nil {
		log.Fatal(err)
	}

	if err := genkit.StartFlowServer(""); err != nil {
		log.Fatal(err)
	}
}
