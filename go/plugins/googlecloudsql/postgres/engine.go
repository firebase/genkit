package postgres

import (
	"context"
	"fmt"
	"net"

	"cloud.google.com/go/cloudsqlconn"
	"github.com/jackc/pgx/v5/pgxpool"
)

type engine struct {
	Pool *pgxpool.Pool
}

// newEngine creates a new Postgres engine.
func newEngine(ctx context.Context, cfg EngineConfig) (*engine, error) {
	pgEngine := new(engine)
	if cfg.ConnPool == nil {
		user, usingIAMAuth, err := getUser(ctx, cfg)
		if err != nil {
			// If no user can be determined, return an error.
			return nil, fmt.Errorf("unable to retrieve a valid username. Err: %w", err)
		}
		if usingIAMAuth {
			cfg.User = user
		}
		cfg.ConnPool, err = createPool(ctx, cfg, usingIAMAuth)
		if err != nil {
			return nil, err
		}
	}

	if err := cfg.ConnPool.Ping(ctx); err != nil {
		return nil, fmt.Errorf("failed to connect with database %v", err)
	}

	pgEngine.Pool = cfg.ConnPool
	return pgEngine, nil
}

// createPool creates a connection pool to the PostgreSQL database.
func createPool(ctx context.Context, cfg EngineConfig, usingIAMAuth bool) (*pgxpool.Pool, error) {
	var dialeropts []cloudsqlconn.Option
	dsn := fmt.Sprintf("user=%s password=%s dbname=%s sslmode=disable", cfg.User, cfg.Password, cfg.Database)
	if usingIAMAuth {
		dialeropts = append(dialeropts, cloudsqlconn.WithIAMAuthN())
		dsn = fmt.Sprintf("user=%s dbname=%s sslmode=disable", cfg.User, cfg.Database)
	}
	d, err := cloudsqlconn.NewDialer(ctx, dialeropts...)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize connection: %w", err)
	}

	config, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to parse connection config: %w", err)
	}
	instanceURI := fmt.Sprintf("projects/%s/locations/%s/clusters/%s/instances/%s", cfg.ProjectID, cfg.Region, cfg.Cluster, cfg.Instance)
	config.ConnConfig.DialFunc = func(ctx context.Context, _ string, _ string) (net.Conn, error) {
		if cfg.IpType == PRIVATE {
			return d.Dial(ctx, instanceURI, cloudsqlconn.WithPrivateIP())
		}
		return d.Dial(ctx, instanceURI, cloudsqlconn.WithPublicIP())
	}
	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		return nil, fmt.Errorf("unable to create connection pool: %w", err)
	}
	return pool, nil
}
