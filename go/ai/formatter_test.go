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

package ai

// func TestMessageParsing(t *testing.T) {
// 	messageTests := []struct {
// 		desc    string
// 		message MessageData
// 		want    []ParsedObject
// 	}{
// 		{
// 			desc: "parses complete JSONL response",
// 			message: MessageData{
// 				Role: "model",
// 				Content: []Content{
// 					{Text: `{"id": 1, "name": "test"}` + "\n" + `{"id": 2}` + "\n"},
// 				},
// 			},
// 			want: []ParsedObject{{ID: 1, Name: "test"}, {ID: 2}},
// 		},
// 		{
// 			desc: "handles empty response",
// 			message: MessageData{
// 				Role:    "model",
// 				Content: []Content{{Text: ""}},
// 			},
// 			want: []ParsedObject{},
// 		},
// 		{
// 			desc: "parses JSONL with preamble and code fence",
// 			message: MessageData{
// 				Role: "model",
// 				Content: []Content{
// 					{Text: "Here are the objects:\n\n```\n{\"id\": 1}\n{\"id\": 2}\n```"},
// 				},
// 			},
// 			want: []ParsedObject{{ID: 1}, {ID: 2}},
// 		},
// 	}

// 	parser := new(JSONLFormatter).handler()

// 	for _, rt := range messageTests {
// 		t.Run(rt.desc, func(t *testing.T) {
// 			got := parser.parseMessage(Message{Data: rt.message})
// 			if !reflect.DeepEqual(got, rt.want) {
// 				t.Errorf("parseMessage() = %v, want %v", got, rt.want)
// 			}
// 		})
// 	}
// }
