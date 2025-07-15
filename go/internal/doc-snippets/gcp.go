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
	"log/slog"
	"time"

	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlecloud"
)

func gcpEx(ctx context.Context) error {
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}
	// [START init]
	plugin := googlecloud.NewWithProjectID("your-google-cloud-project")
	if err := plugin.Init(ctx, g); err != nil {
		return err
	}
	// [END init]

	// Example with custom options
	_ = googlecloud.NewWithProjectID("your-google-cloud-project",
		googlecloud.WithForceExport(true),
		googlecloud.WithMetricInterval(45*time.Second),
		googlecloud.WithLogLevel(slog.LevelDebug),
	)

	// Example with auto-detection
	autoPlugin, err := googlecloud.New(
		googlecloud.WithForceExport(true),
		googlecloud.WithLogLevel(slog.LevelDebug),
	)
	if err != nil {
		return err
	}
	_ = autoPlugin

	return nil
}
