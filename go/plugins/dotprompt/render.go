// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package dotprompt

import (
	"encoding/json"
	"errors"
	"maps"
	"regexp"
	"strings"
	"sync"

	"github.com/aymerick/raymond"
	"github.com/firebase/genkit/go/ai"
)

// RenderText executes the prompt's template and returns the result
// as a string. The result may contain only a single, text, message.
// This just runs the template; it does not call a model.
func (p *Prompt) RenderText(variables map[string]any) (string, error) {
	msgs, err := p.RenderMessages(variables)
	if err != nil {
		return "", err
	}
	if len(msgs) != 1 {
		return "", errors.New("RenderText: multi-message prompt can't be rendered as text")
	}
	var sb strings.Builder
	for _, part := range msgs[0].Content {
		if !part.IsText() {
			return "", errors.New("RenderText: multi-modal prompt can't be rendered as text")
		}
		sb.WriteString(part.Text)
	}
	return sb.String(), nil
}

// RenderMessages executes the prompt's template and converts it into messages.
// This just runs the template; it does not call a model.
func (p *Prompt) RenderMessages(variables map[string]any) ([]*ai.Message, error) {
	if p.DefaultInput != nil {
		nv := make(map[string]any)
		maps.Copy(nv, p.DefaultInput)
		maps.Copy(nv, variables)
		variables = nv
	}
	str, err := p.Template.Exec(variables)
	if err != nil {
		return nil, err
	}
	return p.toMessages(str)
}

const rolePrefix = "<<<dotprompt:role:"
const roleSuffix = ">>>"
const roleMatch = rolePrefix + "[a-z]+" + roleSuffix

var roleRegexp = sync.OnceValue(func() *regexp.Regexp {
	return regexp.MustCompile(roleMatch)
})

const mediaPrefix = "<<<dotprompt:media:url"
const mediaSuffix = ">>>"
const mediaMatch = mediaPrefix + ".*?" + mediaSuffix

var mediaRegexp = sync.OnceValue(func() *regexp.Regexp {
	return regexp.MustCompile(mediaMatch)
})

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

// toMessages converts the rendered prompt into a series of messages,
// by splitting it on a magic regular expression.
// This implements the "role" dotprompt helper function.
func (p *Prompt) toMessages(str string) ([]*ai.Message, error) {
	type messageSource struct {
		role   ai.Role
		source string
	}

	var msgs []*messageSource
	msg := &messageSource{
		role: ai.RoleUser,
	}

	roleIndexes := roleRegexp().FindAllStringIndex(str, -1)
	i := 0
	for _, m := range roleIndexes {
		if m[0] > i {
			add := str[i:m[0]]
			if strings.TrimSpace(add) != "" {
				msg.source += add
			}
		}
		if msg.source != "" {
			msgs = append(msgs, msg)
			msg = &messageSource{}
		}
		msg.role = ai.Role(str[m[0]+len(rolePrefix) : m[1]-len(roleSuffix)])
		i = m[1]
	}
	if i < len(str) {
		msg.source += str[i:]
	}
	if msg.source != "" {
		msgs = append(msgs, msg)
	}

	aiMsgs := make([]*ai.Message, 0, len(msgs))
	for _, msg := range msgs {
		aiMsg := &ai.Message{
			Role:    msg.role,
			Content: p.toParts(msg.source),
		}
		aiMsgs = append(aiMsgs, aiMsg)
	}

	return aiMsgs, nil
}

// toParts builds the parts of a message based on a magic regexp.
// This implements the "media" dotprompt helper function.
func (p *Prompt) toParts(str string) []*ai.Part {
	var ret []*ai.Part
	mediaIndexes := mediaRegexp().FindAllStringIndex(str, -1)
	i := 0
	for _, m := range mediaIndexes {
		if m[0] > i {
			add := str[i:m[0]]
			if strings.TrimSpace(add) != "" {
				ret = append(ret, ai.NewTextPart(add))
			}
		}

		media := str[m[0]+len(mediaPrefix) : m[1]-len(mediaSuffix)]
		url, contentType, _ := strings.Cut(media, " ")
		ret = append(ret, ai.NewMediaPart(contentType, url))

		i = m[1]
	}
	if i < len(str) {
		ret = append(ret, ai.NewTextPart(str[i:]))
	}
	return ret
}
