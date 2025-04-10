package modelgarden_test

import (
	"context"
	"flag"
	"log"
	"testing"

	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/vertexai/modelgarden"
	"github.com/firebase/genkit/go/plugins/vertexai/modelgarden/anthropic"
)

var (
	provider  = flag.String("provider", "", "Modelgarden provider to test against")
	projectID = flag.String("projectid", "", "Modelgarden project")
	location  = flag.String("location", "us-east5", "Geographic location")
)

func TestAnthropicLive(t *testing.T) {
	if *provider != "anthropic" {
		t.Skipf("skipping Anthropic")
	}

	ctx := context.Background()
	g, err := genkit.Init(ctx, genkit.WithPlugins(modelgarden.WithProviders(&anthropic.Anthropic{})))
	if err != nil {
		log.Fatal(err)
	}

	t.Run("invalid model", func(t *testing.T) {
		m := anthropic.Model(g, "claude-not-valid-v2")
		if m != nil {
			t.Fatalf("model should have been empty, got: %#v", m)
		}
	})
}
