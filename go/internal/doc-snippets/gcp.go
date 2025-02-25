// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package snippets

import (
	"context"
	"log"
	"log/slog"

	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlecloud"
)

func gcpEx(ctx context.Context) error {
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}
	// [START init]
	if err := googlecloud.Init(
		ctx,
		g,
		googlecloud.Config{ProjectID: "your-google-cloud-project"},
	); err != nil {
		return err
	}
	// [END init]

	_ = googlecloud.Config{
		ProjectID:      "your-google-cloud-project",
		ForceExport:    true,
		MetricInterval: 45e9,
		LogLevel:       slog.LevelDebug,
	}

	return nil
}
