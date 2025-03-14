// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"reflect"
	"strings"
)

// Schema represents a JSON Schema.
// It can be used with encoding/json to read or write one.
type Schema struct {
	SchemaVersion        string                   `json:"$schema,omitempty"`
	ID                   string                   `json:"$id,omitempty"`
	Type                 *OneOf[string, []string] `json:"type,omitempty"`
	Description          string                   `json:"description,omitempty"`
	Properties           map[string]*Schema       `json:"properties,omitempty"`
	AdditionalProperties *Schema                  `json:"additionalProperties,omitempty"`
	Const                bool                     `json:"const,omitempty"`
	Required             []string                 `json:"required,omitempty"`
	Items                *Schema                  `json:"items,omitempty"`
	Enum                 []string                 `json:"enum,omitempty"`
	Not                  any                      `json:"not,omitempty"`
	AnyOf                []*Schema                `json:"anyOf,omitempty"`
	AllOf                []*Schema                `json:"allOf,omitempty"`
	Default              any                      `json:"default,omitempty"`
	Ref                  string                   `json:"$ref,omitempty"`
	Defs                 map[string]*Schema       `json:"$defs,omitempty"`
}

// UnmarshalJSON is necessary to handle the cases "true" and "false", which
// are valid JSON Schemas.

var (
	trueBytes  = []byte("true")
	falseBytes = []byte("false")
	nullBytes  = []byte("null")
)

func (s *Schema) UnmarshalJSON(data []byte) error {
	// Assume *s is zero.
	if bytes.Equal(data, trueBytes) {
		return nil
	}
	if bytes.Equal(data, falseBytes) {
		// False is equivalent to {"not": {}}.
		s.Not = &Schema{}
		return nil
	}
	type nomethod *Schema
	return json.Unmarshal(data, nomethod(s))
}

var fields = reflect.VisibleFields(reflect.TypeOf(Schema{}))

func (s *Schema) String() string {
	sv := reflect.ValueOf(s).Elem()
	var ss []string
	for _, f := range fields {
		fv := sv.FieldByIndex(f.Index)
		if !fv.IsZero() {
			ss = append(ss, fmt.Sprintf("%s: %v", f.Name, fv))
		}
	}
	return "{" + strings.Join(ss, ", ") + "}"
}

// OneOf[T1, T2] JSON-unmarshals as either a T1 or a T2.
type OneOf[T1, T2 any] struct{ any }

func (o *OneOf[T1, T2]) UnmarshalJSON(data []byte) error {
	if bytes.Equal(data, nullBytes) {
		return nil
	}

	var t1 T1
	if err := json.Unmarshal(data, &t1); err == nil {
		o.any = t1
		return nil
	}
	var t2 T2
	if err := json.Unmarshal(data, &t2); err == nil {
		o.any = t2
		return nil
	}
	return fmt.Errorf("could not unmarshal %q as %T or %T", data, t1, t2)
}

func (o *OneOf[T1, T2]) MarshalJSON() ([]byte, error) {
	if o == nil {
		return nullBytes, nil
	}
	return json.Marshal(o.any)
}

func (o *OneOf[T1, T2]) Any() any {
	if o == nil {
		return nil
	}
	return o.any
}
