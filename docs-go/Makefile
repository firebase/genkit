WEAVE=$(HOME)/go/bin/weave 

all: $(WEAVE) flows.md models.md prompts.md

$(WEAVE): ../go/internal/cmd/weave/*.go
	go -C ../go install ./internal/cmd/weave
		
%.md: %.src
	$(WEAVE) $< > $@

