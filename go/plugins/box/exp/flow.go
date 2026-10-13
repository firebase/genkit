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

package exp

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/genkit"
)

// NewFlow returns an unregistered proxy for the flow named name in the box.
// The schemas come from In and Out, or from [WithInputSchema] /
// [WithOutputSchema] when In / Out are any.
//
//	summarize := box.NewFlow[any, any](b, "summarize",
//		box.WithInputSchema(in), box.WithOutputSchema(out))
func NewFlow[In, Out any](b *Box, name string, opts ...ProxyOption) *core.Flow[In, Out, struct{}] {
	return newFlowProxy[In, Out, struct{}](b, name, name, checkedFlowOptions[In, Out, struct{}](name, opts), false)
}

// DefineFlow is [NewFlow] that also registers the proxy.
func DefineFlow[In, Out any](b *Box, name string, opts ...ProxyOption) *core.Flow[In, Out, struct{}] {
	f := NewFlow[In, Out](b, name, opts...)
	genkit.RegisterAction(b.g, f)
	return f
}

// NewStreamingFlow returns an unregistered proxy for the streaming flow named
// name in the box; chunks the box streams arrive as Stream values.
func NewStreamingFlow[In, Out, Stream any](b *Box, name string, opts ...ProxyOption) *core.Flow[In, Out, Stream] {
	return newFlowProxy[In, Out, Stream](b, name, name, checkedFlowOptions[In, Out, Stream](name, opts), true)
}

// DefineStreamingFlow is [NewStreamingFlow] that also registers the proxy.
func DefineStreamingFlow[In, Out, Stream any](b *Box, name string, opts ...ProxyOption) *core.Flow[In, Out, Stream] {
	f := NewStreamingFlow[In, Out, Stream](b, name, opts...)
	genkit.RegisterAction(b.g, f)
	return f
}

// NewFlowFrom returns an unregistered proxy for a real flow: same name,
// description and schemas, with every run happening in the box.
func NewFlowFrom[In, Out, Stream any](b *Box, f *core.Flow[In, Out, Stream]) *core.Flow[In, Out, Stream] {
	desc := f.Desc()
	return newFlowProxy[In, Out, Stream](b, desc.Name, desc.Name, flowSchemas(desc), desc.StreamSchema != nil)
}

// DefineFlowFrom is [NewFlowFrom] that also registers the proxy under name,
// which must differ from the flow's own (see [DefineToolFrom]).
func DefineFlowFrom[In, Out, Stream any](b *Box, f *core.Flow[In, Out, Stream], name string) *core.Flow[In, Out, Stream] {
	desc := f.Desc()
	if name == desc.Name {
		panic(fmt.Errorf("box.DefineFlowFrom: the proxy must be renamed (got %q, same as the original)", name))
	}
	p := newFlowProxy[In, Out, Stream](b, name, desc.Name, flowSchemas(desc), desc.StreamSchema != nil)
	genkit.RegisterAction(b.g, p)
	return p
}

// checkedFlowOptions applies opts and checks that each explicit schema stands
// in for a type parameter of any.
func checkedFlowOptions[In, Out, Stream any](name string, opts []ProxyOption) *proxyOptions {
	o := applyProxyOptions(opts)
	if o.inputSchema != nil {
		requireAny[In]("box flow", name, "an input schema")
	}
	if o.outputSchema != nil {
		requireAny[Out]("box flow", name, "an output schema")
	}
	if o.streamSchema != nil {
		requireAny[Stream]("box flow", name, "a stream schema")
	}
	return o
}

// flowSchemas copies a flow's descriptor so its proxy advertises exactly the
// same schemas, explicit or inferred.
func flowSchemas(desc api.ActionDesc) *proxyOptions {
	return &proxyOptions{
		description:  desc.Description,
		inputSchema:  desc.InputSchema,
		outputSchema: desc.OutputSchema,
		streamSchema: desc.StreamSchema,
	}
}

// newFlowProxy builds a flow named name that runs the flow target in the box.
// Explicit schemas are passed straight to the descriptor; the type check
// applies only to the public spec constructors, since a From proxy copies
// schemas that already agree with its types.
func newFlowProxy[In, Out, Stream any](b *Box, name, target string, o *proxyOptions, streaming bool) *core.Flow[In, Out, Stream] {
	key := actionKey(api.ActionTypeFlow, target)
	a := core.NewStreamingActionOf(api.ActionTypeFlow, name, &core.ActionOptions{
		Description:  o.description,
		Metadata:     map[string]any{"box": b.id},
		InputSchema:  o.inputSchema,
		OutputSchema: o.outputSchema,
		StreamSchema: o.streamSchema,
	}, func(ctx context.Context, input In, cb core.StreamCallback[Stream]) (Out, error) {
		var zero Out
		// Like core.NewFlow, so genkit.Run steps work under the proxy span.
		ctx = core.WithFlowContext(ctx, name)
		in, err := json.Marshal(input)
		if err != nil {
			return zero, fmt.Errorf("box flow %q: marshal input: %w", name, err)
		}
		var opts *RunOptions
		if streaming && cb != nil {
			opts = &RunOptions{OnChunk: func(ctx context.Context, raw json.RawMessage) error {
				chunk, err := decodeJSON[Stream](raw, fmt.Sprintf("flow %q chunk", name))
				if err != nil {
					return err
				}
				return cb(ctx, chunk)
			}}
		}
		raw, err := b.call(ctx, &RunActionRequest{Key: key, Input: in}, opts)
		if err != nil {
			return zero, err
		}
		return decodeJSON[Out](raw, fmt.Sprintf("flow %q output", name))
	})
	return &core.Flow[In, Out, Stream]{Action: a}
}
