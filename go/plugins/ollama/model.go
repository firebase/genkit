package ollama

import (
	"encoding/json"
	"errors"

	"github.com/firebase/genkit/go/ai"
)

var allowedOllamaOptions = map[string]string{
	"seed":        "opts",
	"temperature": "opts",
	"top_k":       "opts",
	"top_p":       "opts",
	"min_p":       "opts",
	"stop":        "opts",
	"num_ctx":     "opts",
	"num_predict": "opts",
	"think":       "main",
	"keep_alive":  "main",
}

// Ollama has two API endpoints, one with a chat interface and another with a generate response interface.
// That's why have multiple request interfaces for the Ollama API below.

/*
TODO: Support optional, advanced parameters:
format: the format to return a response in. Currently the only accepted value is json
options: additional model parameters listed in the documentation for the Modelfile such as temperature
system: system message to (overrides what is defined in the Modelfile)
template: the prompt template to use (overrides what is defined in the Modelfile)
context: the context parameter returned from a previous request to /generate, this can be used to keep a short conversational memory
stream: if false the response will be returned as a single response object, rather than a stream of objects
raw: if true no formatting will be applied to the prompt. You may choose to use the raw parameter if you are specifying a full templated prompt in your request to the API
keep_alive: controls how long the model will stay loaded into memory following the request (default: 5m)
*/
type ollamaChatRequest struct {
	Messages  []*ollamaMessage `json:"messages"`
	Images    []string         `json:"images,omitempty"`
	Model     string           `json:"model"`
	Stream    bool             `json:"stream"`
	Format    string           `json:"format,omitempty"`
	Tools     []ollamaTool     `json:"tools,omitempty"`
	Think     any              `json:"think,omitempty"`
	Options   map[string]any   `json:"options,omitempty"`
	KeepAlive string           `json:"keep_alive,omitempty"`
}

func (o *ollamaChatRequest) ApplyOptions(cfg any) error {
	if cfg == nil {
		return nil
	}

	switch cfg := cfg.(type) {
	case GenerateContentConfig:
		o.applyGenerateContentConfig(&cfg)
		return nil
	case *GenerateContentConfig:
		o.applyGenerateContentConfig(cfg)
		return nil
	case map[string]any:
		return o.applyMapAny(cfg)
	case *ai.GenerationCommonConfig:
		return o.applyGenerationCommonConfig(cfg)
	case ai.GenerationCommonConfig:
		return o.applyGenerationCommonConfig(&cfg)
	default:
		return errors.New("unknown generation config")
	}
}
func (o *ollamaChatRequest) applyGenerateContentConfig(cfg *GenerateContentConfig) {
	if cfg == nil {
		return
	}

	// thinking
	if cfg.Think != nil {
		o.Think = cfg.Think
	}

	// runtime options
	opts := map[string]any{}

	if cfg.Seed != nil {
		opts["seed"] = *cfg.Seed
	}
	if cfg.Temperature != nil {
		opts["temperature"] = *cfg.Temperature
	}
	if cfg.TopK != nil {
		opts["top_k"] = *cfg.TopK
	}
	if cfg.TopP != nil {
		opts["top_p"] = *cfg.TopP
	}
	if cfg.MinP != nil {
		opts["min_p"] = *cfg.MinP
	}
	if len(cfg.Stop) > 0 {
		opts["stop"] = cfg.Stop
	}
	if cfg.NumCtx != nil {
		opts["num_ctx"] = *cfg.NumCtx
	}
	if cfg.NumPredict != nil {
		opts["num_predict"] = *cfg.NumPredict
	}

	if len(opts) > 0 {
		o.Options = opts
	}
}
func (o *ollamaChatRequest) applyGenerationCommonConfig(cfg *ai.GenerationCommonConfig) error {
	opts := map[string]any{}
	b, err := json.Marshal(cfg)
	if err != nil {
		return err
	}

	err = json.Unmarshal(b, &opts)
	if err != nil {
		return err
	}

	if len(opts) > 0 {
		o.Options = opts
	}
	return nil
}
func (o *ollamaChatRequest) applyMapAny(m map[string]any) error {
	if len(m) == 0 {
		return nil
	}

	opts := map[string]any{}

	for k, v := range m {
		typeVal, ok := allowedOllamaOptions[k]
		if !ok {
			return errors.New("unknown option: " + k)
		}
		switch typeVal {
		case "main":
			switch k {
			case "think":
				o.Think = v
			case "keep_alive":
				if s, ok := v.(string); ok {
					o.KeepAlive = s
				} else {
					return errors.New("keep_alive must be string")
				}
			}

		case "opts":
			opts[k] = v
		}

	}

	if len(opts) > 0 {
		o.Options = opts
	}
	return nil
}
