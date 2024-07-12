WEAVE=$(HOME)/go/bin/weave 

all: $(WEAVE) get-started-go.md flows.md models.md prompts.md dotprompt.md pgvector.md \
	cloud-run.md rag.md \
	plugins/ollama.md plugins/pinecone.md plugins/google-genai.md plugins/vertex-ai.md

$(WEAVE): ../go/internal/cmd/weave/*.go
	go -C ../go install ./internal/cmd/weave
		
%.md: %.src
	$(WEAVE) $< > $@
