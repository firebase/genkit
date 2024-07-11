WEAVE=$(HOME)/go/bin/weave 

all: $(WEAVE) get-started-go.md flows.md models.md prompts.md dotprompt.md pgvector.md

$(WEAVE): ../go/internal/cmd/weave/*.go
	go -C ../go install ./internal/cmd/weave
		
%.md: %.src
	$(WEAVE) $< > $@

