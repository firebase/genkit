package postgres

import (
	"context"
	"errors"
	"fmt"
	"github.com/jackc/pgx/v5/pgxpool"
	"golang.org/x/oauth2/google"
	"google.golang.org/api/oauth2/v2"
	"google.golang.org/api/option"
)

// EmailRetriever func(context.Context) (string, error)
type EmailRetriever func(context.Context) (string, error)

type EngineConfig struct {
	ProjectID       string
	Region          string
	Cluster         string
	Instance        string
	ConnPool        *pgxpool.Pool
	Database        string
	User            string
	Password        string
	IpType          IpType
	IAMAccountEmail string
	EmailRetreiver  EmailRetriever
}

// IpType type of IP address, public or private
type IpType string

const (
	PUBLIC  IpType = "PUBLIC"
	PRIVATE IpType = "PRIVATE"
)

func validateEngineConfig(cfg *EngineConfig) error {
	if cfg.IpType == "" {
		cfg.IpType = PUBLIC
	}

	if cfg.EmailRetreiver == nil {
		cfg.EmailRetreiver = getServiceAccountEmail
	}

	if cfg.ConnPool == nil && (cfg.ProjectID == "" || cfg.Region == "" || cfg.Cluster == "" || cfg.Instance == "") {
		return errors.New("missing connection: provide a connection pool or db instance fields")
	}
	if cfg.Database == "" {
		return errors.New("missing database field")
	}
	return nil
}

// getUser retrieves the username, a flag indicating if IAM authentication
// will be used and an error.
func getUser(ctx context.Context, config EngineConfig) (string, bool, error) {
	if config.User != "" && config.Password != "" {
		// If both username and password are provided use provided username.
		return config.User, false, nil
	}
	if config.IAMAccountEmail != "" {
		// If iamAccountEmail is provided use it as user.
		return config.IAMAccountEmail, true, nil
	}
	// If neither user and password nor iamAccountEmail are provided,
	// retrieve IAM email from the environment.
	serviceAccountEmail, err := config.EmailRetreiver(ctx)
	if err != nil {
		return "", false, fmt.Errorf("unable to retrieve service account email: %w", err)
	}
	return serviceAccountEmail, true, nil

}

// getServiceAccountEmail retrieves the IAM principal email with users account.
func getServiceAccountEmail(ctx context.Context) (string, error) {
	scopes := []string{"https://www.googleapis.com/auth/userinfo.email"}
	// Get credentials using email scope
	credentials, err := google.FindDefaultCredentials(ctx, scopes...)
	if err != nil {
		return "", fmt.Errorf("unable to get default credentials: %w", err)
	}

	// Verify valid TokenSource.
	if credentials.TokenSource == nil {
		return "", fmt.Errorf("missing or invalid credentials")
	}

	oauth2Service, err := oauth2.NewService(ctx, option.WithTokenSource(credentials.TokenSource))
	if err != nil {
		return "", fmt.Errorf("failed to create new service: %w", err)
	}

	// Fetch IAM principal email.
	userInfo, err := oauth2Service.Userinfo.Get().Do()
	if err != nil {
		return "", fmt.Errorf("failed to get user info: %w", err)
	}
	return userInfo.Email, nil
}
