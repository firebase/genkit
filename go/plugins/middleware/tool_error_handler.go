// Copyright 2026 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package middleware

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
)

// ToolErrorHandler catches non-interrupt tool execution errors and returns
// them as tool responses with a text part describing the failure. This allows
// the model to see and react to tool failures instead of aborting the entire
// generation loop.
//
// Usage:
//
//	resp, err := ai.Generate(ctx, r,
//	    ai.WithModel(m),
//	    ai.WithPrompt("do something"),
//	    ai.WithTools(toolA, toolB),
//	    ai.WithUse(&middleware.ToolErrorHandler{}),
//	)
type ToolErrorHandler struct {
	ai.BaseMiddleware
}

func (t *ToolErrorHandler) Name() string { return provider + "/toolErrorHandler" }

func (t *ToolErrorHandler) New() ai.Middleware {
	return &ToolErrorHandler{}
}

func (t *ToolErrorHandler) WrapTool(ctx context.Context, params *ai.ToolParams, next ai.ToolNext) (*ai.ToolResponse, error) {
	resp, err := next(ctx, params)
	if err != nil {
		if isInterrupt, _ := ai.IsToolInterruptError(err); isInterrupt {
			return nil, err
		}
		return &ai.ToolResponse{
			Content: []*ai.Part{
				ai.NewTextPart(fmt.Sprintf("tool %q failed: %v", params.Tool.Name(), err)),
			},
		}, nil
	}
	return resp, nil
}
