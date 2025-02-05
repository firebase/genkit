package ai

import (
	"context"
	"os"
	"testing"

	"github.com/firebase/genkit/go/internal/registry"
	"github.com/google/go-cmp/cmp"
	"github.com/google/go-cmp/cmp/cmpopts"
	"gopkg.in/yaml.v3"
)

type specSuite struct {
	Tests []testCase `yaml:"tests"`
}

type testCase struct {
	Name           string                  `yaml:"name"`
	Input          *GenerateActionOptions  `yaml:"input"`
	StreamChunks   [][]*ModelResponseChunk `yaml:"streamChunks,omitempty"`
	ModelResponses []*ModelResponse        `yaml:"modelResponses"`
	ExpectResponse *ModelResponse          `yaml:"expectResponse,omitempty"`
	Stream         bool                    `yaml:"stream,omitempty"`
	ExpectChunks   []*ModelResponseChunk   `yaml:"expectChunks,omitempty"`
}

type programmableModel struct {
	r           *registry.Registry
	handleResp  func(ctx context.Context, req *ModelRequest, cb func(context.Context, *ModelResponseChunk) error) (*ModelResponse, error)
	lastRequest *ModelRequest
}

func (pm *programmableModel) Name() string {
	return "programmableModel"
}

func (pm *programmableModel) Generate(ctx context.Context, r *registry.Registry, req *ModelRequest, toolCfg *ToolConfig, cb func(context.Context, *ModelResponseChunk) error) (*ModelResponse, error) {
	pm.lastRequest = req
	return pm.handleResp(ctx, req, cb)
}

func defineProgrammableModel(r *registry.Registry) *programmableModel {
	pm := &programmableModel{r: r}
	DefineModel(r, "default", "programmableModel", nil, func(ctx context.Context, req *ModelRequest, cb ModelStreamingCallback) (*ModelResponse, error) {
		return pm.Generate(ctx, r, req, &ToolConfig{MaxTurns: 5}, cb)
	})
	return pm
}

func TestGenerateAction(t *testing.T) {
	cmpopts := cmp.Options{
		cmpopts.EquateEmpty(),
	}

	data, err := os.ReadFile("../../tests/specs/generate.yaml")
	if err != nil {
		t.Fatalf("failed to read spec file: %v", err)
	}

	var suite specSuite
	if err := yaml.Unmarshal(data, &suite); err != nil {
		t.Fatalf("failed to parse spec file: %v", err)
	}

	for _, tc := range suite.Tests {
		t.Run(tc.Name, func(t *testing.T) {
			ctx := context.Background()

			r, err := registry.New()
			if err != nil {
				t.Fatalf("failed to create registry: %v", err)
			}

			pm := defineProgrammableModel(r)

			DefineTool(r, "testTool", "description",
				func(ctx *ToolContext, input any) (any, error) {
					return "tool called", nil
				})

			if len(tc.ModelResponses) > 0 || len(tc.StreamChunks) > 0 {
				reqCounter := 0
				pm.handleResp = func(ctx context.Context, req *ModelRequest, cb func(context.Context, *ModelResponseChunk) error) (*ModelResponse, error) {
					if len(tc.StreamChunks) > 0 && cb != nil {
						for _, chunk := range tc.StreamChunks[reqCounter] {
							if err := cb(ctx, chunk); err != nil {
								return nil, err
							}
						}
					}
					resp := tc.ModelResponses[reqCounter]
					resp.Request = req
					reqCounter++
					return resp, nil
				}
			}

			genAction := DefineGenerateAction(ctx, r)

			if tc.Stream {
				chunks := []*ModelResponseChunk{}
				streamCb := func(ctx context.Context, chunk *ModelResponseChunk) error {
					chunks = append(chunks, chunk)
					return nil
				}

				resp, err := genAction.Run(ctx, tc.Input, streamCb)
				if err != nil {
					t.Fatalf("action failed: %v", err)
				}

				if diff := cmp.Diff(tc.ExpectChunks, chunks); diff != "" {
					t.Errorf("chunks mismatch (-want +got):\n%s", diff)
				}

				if diff := cmp.Diff(tc.ExpectResponse, resp, cmpopts); diff != "" {
					t.Errorf("response mismatch (-want +got):\n%s", diff)
				}
			} else {
				resp, err := genAction.Run(ctx, tc.Input, nil)
				if err != nil {
					t.Fatalf("action failed: %v", err)
				}

				if diff := cmp.Diff(tc.ExpectResponse, resp, cmpopts); diff != "" {
					t.Errorf("response mismatch (-want +got):\n%s", diff)
				}
			}
		})
	}
}
