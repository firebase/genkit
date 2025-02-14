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

package prompt

import (
	"encoding/json"
	"fmt"
	"maps"
	"strings"

	"github.com/aymerick/raymond"
)

const rolePrefix = "<<<dotprompt:role:"
const roleSuffix = ">>>"
const mediaPrefix = "<<<dotprompt:media:url"
const mediaSuffix = ">>>"

// jsonHelper is an undocumented template execution helper.
func jsonHelper(v any, options *raymond.Options) raymond.SafeString {
	indent := 0
	if indentArg := options.HashProp("indent"); indentArg != nil {
		indent, _ = indentArg.(int)
	}
	var data []byte
	var err error
	if indent == 0 {
		data, err = json.Marshal(v)
	} else {
		data, err = json.MarshalIndent(v, "", strings.Repeat(" ", indent))
	}
	if err != nil {
		return raymond.SafeString(err.Error())
	}
	return raymond.SafeString(data)
}

// roleHelper changes roles.
func roleHelper(role string) raymond.SafeString {
	return raymond.SafeString(rolePrefix + role + roleSuffix)
}

// mediaHelper inserts media.
func mediaHelper(options *raymond.Options) raymond.SafeString {
	url := options.HashStr("url")
	contentType := options.HashStr("contentType")
	add := url
	if contentType != "" {
		add += " " + contentType
	}
	return raymond.SafeString(mediaPrefix + add + mediaSuffix)
}

// templateHelpers is the helpers supported by all dotprompt templates.
var templateHelpers = map[string]any{
	"json":  jsonHelper,
	"role":  roleHelper,
	"media": mediaHelper,
}

// RenderMessages executes the prompt's template and converts it into messages.
// This just runs the template; it does not call a model.
func renderDotprompt(templateText string, variables map[string]any, defaultInput map[string]any) (string, error) {
	template, err := raymond.Parse(templateText)
	if err != nil {
		return "", fmt.Errorf("renderDotprompt: failed to parse: %w", err)
	}
	template.RegisterHelpers(templateHelpers)

	if defaultInput != nil {
		nv := make(map[string]any)
		maps.Copy(nv, defaultInput)
		maps.Copy(nv, variables)
		variables = nv
	}
	str, err := template.Exec(variables)
	if err != nil {
		return "", err
	}
	return str, nil
}
