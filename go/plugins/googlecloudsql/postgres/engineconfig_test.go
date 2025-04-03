package postgres

import (
	"context"
	"errors"
	"fmt"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/stretchr/testify/assert"
)

func TestValidateEngineConfig(t *testing.T) {
	mockEmailRetriever := func(ctx context.Context) (string, error) {
		return "test@google.com", nil
	}

	testCases := []struct {
		name               string
		cfg                *EngineConfig
		wantErr            bool
		wantIpType         IpType
		wantEmailRetriever EmailRetriever
	}{
		{
			name: "valid config with connection pool",
			cfg: &EngineConfig{
				ConnPool: &pgxpool.Pool{},
				Database: "testdb",
			},
			wantErr:            false,
			wantIpType:         PUBLIC,
			wantEmailRetriever: getServiceAccountEmail,
		},
		{
			name: "valid config with instance details",
			cfg: &EngineConfig{
				ProjectID: "testproject",
				Region:    "testregion",
				Cluster:   "testcluster",
				Instance:  "testinstance",
				Database:  "testdb",
			},
			wantErr:            false,
			wantIpType:         PUBLIC,
			wantEmailRetriever: getServiceAccountEmail,
		},
		{
			name: "missing database",
			cfg: &EngineConfig{
				ProjectID: "testproject",
				Region:    "testregion",
				Cluster:   "testcluster",
				Instance:  "testinstance",
			},
			wantErr:            true,
			wantIpType:         PUBLIC,
			wantEmailRetriever: getServiceAccountEmail,
		},
		{
			name: "missing all connection details",
			cfg: &EngineConfig{
				Database: "testdb",
			},
			wantErr:            true,
			wantIpType:         PUBLIC,
			wantEmailRetriever: getServiceAccountEmail,
		},
		{
			name: "ip type private",
			cfg: &EngineConfig{
				ProjectID: "testproject",
				Region:    "testregion",
				Cluster:   "testcluster",
				Instance:  "testinstance",
				Database:  "testdb",
				IpType:    PRIVATE,
			},
			wantErr:            false,
			wantIpType:         PRIVATE,
			wantEmailRetriever: getServiceAccountEmail,
		},
		{
			name: "custom EmailRetriever",
			cfg: &EngineConfig{
				ProjectID:      "testproject",
				Region:         "testregion",
				Cluster:        "testcluster",
				Instance:       "testinstance",
				Database:       "testdb",
				EmailRetreiver: mockEmailRetriever,
			},
			wantErr:            false,
			wantIpType:         PUBLIC,
			wantEmailRetriever: mockEmailRetriever,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			err := validateEngineConfig(tc.cfg)
			if tc.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
				assert.Equal(t, tc.wantIpType, tc.cfg.IpType)
				assert.NotNil(t, tc.cfg.EmailRetreiver)
				assert.Equal(t, fmt.Sprintf("%p", tc.wantEmailRetriever), fmt.Sprintf("%p", tc.cfg.EmailRetreiver))
			}
		})
	}
}

func TestGetUser(t *testing.T) {
	testCases := []struct {
		name               string
		cfg                EngineConfig
		wantUser           string
		wantIAMAuth        bool
		wantErr            bool
		mockEmailRetriever EmailRetriever
	}{
		{
			name: "user and password provided",
			cfg: EngineConfig{
				User:     "testuser",
				Password: "testpassword",
			},
			wantUser:    "testuser",
			wantIAMAuth: false,
			wantErr:     false,
		},
		{
			name: "iam account email provided",
			cfg: EngineConfig{
				IAMAccountEmail: "iam@example.com",
			},
			wantUser:    "iam@example.com",
			wantIAMAuth: true,
			wantErr:     false,
		},
		{
			name: "retrieve service account email success",
			cfg: EngineConfig{
				EmailRetreiver: func(ctx context.Context) (string, error) {
					return "service@example.com", nil
				},
			},
			wantUser:    "service@example.com",
			wantIAMAuth: true,
			wantErr:     false,
		},
		{
			name: "retrieve service account email failure",
			cfg: EngineConfig{
				EmailRetreiver: func(ctx context.Context) (string, error) {
					return "", errors.New("retrieve error")
				},
			},
			wantUser:    "",
			wantIAMAuth: false,
			wantErr:     true,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			ctx := context.Background()
			user, iamAuth, err := getUser(ctx, tc.cfg)
			if tc.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
				assert.Equal(t, tc.wantUser, user)
				assert.Equal(t, tc.wantIAMAuth, iamAuth)
			}
		})
	}
}
