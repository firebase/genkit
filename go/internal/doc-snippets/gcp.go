package snippets

import (
	"context"
	"log/slog"

	"github.com/firebase/genkit/go/plugins/googlecloud"
)

func gcpEx(ctx context.Context) error {
	//!+init
	if err := googlecloud.Init(
		ctx,
		googlecloud.Config{ProjectID: "your-google-cloud-project"},
	); err != nil {
		return err
	}
	//!-init

	_ = googlecloud.Config{
		ProjectID:      "your-google-cloud-project",
		ForceExport:    true,
		MetricInterval: 45e9,
		LogLevel:       slog.LevelDebug,
	}

	return nil
}
