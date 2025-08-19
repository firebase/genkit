// Copyright 2025 Google LLC
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

package snippets

import (
	"context"
	"log"

	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlecloud"
)

func gcpEx(ctx context.Context) error {
	// [START init]
	googlecloud.EnableGoogleCloudTelemetry()
	// [END init]

	_, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// Example with custom configuration
	googlecloud.EnableGoogleCloudTelemetry(&googlecloud.GoogleCloudTelemetryOptions{
		ProjectID:                    "your-google-cloud-project",
		ForceDevExport:               true,
		DisableLoggingInputAndOutput: false,
	})

	return nil
}
