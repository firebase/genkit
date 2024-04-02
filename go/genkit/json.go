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

package genkit

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
)

// jsonString returns json.Marshal(x) as a string. If json.Marshal returns
// an error, jsonString returns the error text as a JSON string beginning "ERROR:".
func jsonString(x any) string {
	bytes, err := json.Marshal(x)
	if err != nil {
		bytes, _ = json.Marshal(fmt.Sprintf("ERROR: %v", err))
	}
	return string(bytes)
}

// writeJSONFile writes value to filename as JSON.
func writeJSONFile(filename string, value any) error {
	f, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer func() {
		err = errors.Join(err, f.Close())
	}()
	enc := json.NewEncoder(f)
	enc.SetIndent("", "    ") // make the trace easy to read for debugging
	return enc.Encode(value)
}

// readJSONFile JSON-decodes the contents of filename into pvalue.
func readJSONFile(filename string, pvalue any) error {
	f, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer f.Close()
	return json.NewDecoder(f).Decode(pvalue)
}
