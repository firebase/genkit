package postgresql

import (
	"context"
	"errors"
	"fmt"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/stretchr/testify/assert"
)

func TestApplyEngineOptionsConfig(t *testing.T) {
	mockEmailRetriever := func(ctx context.Context) (string, error) {
		return "test@google.com", nil
	}

	testCases := []struct {
		name               string
		opts               []Option
		wantErr            bool
		wantIpType         IpType
		wantEmailRetriever EmailRetriever
	}{
		{
			name: "valid config with connection pool",
			opts: []Option{
				WithPool(&pgxpool.Pool{}),
				WithDatabase("testdb"),
			},
			wantErr:            false,
			wantIpType:         PUBLIC,
			wantEmailRetriever: getServiceAccountEmail,
		},
		{
			name: "valid config with instance details",
			opts: []Option{
				WithCloudSQLInstance("testproject", "testregion", "testinstance"),
				WithDatabase("testdb"),
			},
			wantErr:            false,
			wantIpType:         PUBLIC,
			wantEmailRetriever: getServiceAccountEmail,
		},
		{
			name: "missing database",
			opts: []Option{
				WithCloudSQLInstance("testproject", "testregion", "testinstance"),
			},
			wantErr:            true,
			wantIpType:         PUBLIC,
			wantEmailRetriever: getServiceAccountEmail,
		},
		{
			name: "missing all connection details",
			opts: []Option{
				WithDatabase("testdb"),
			},
			wantErr:            true,
			wantIpType:         PUBLIC,
			wantEmailRetriever: getServiceAccountEmail,
		},
		{
			name: "ip type private",
			opts: []Option{
				WithCloudSQLInstance("testproject", "testregion", "testinstance"),
				WithDatabase("testdb"),
				WithIPType(PRIVATE),
			},
			wantErr:            false,
			wantIpType:         PRIVATE,
			wantEmailRetriever: getServiceAccountEmail,
		},
		{
			name: "custom EmailRetriever",
			opts: []Option{
				WithCloudSQLInstance("testproject", "testregion", "testinstance"),
				WithDatabase("testdb"),
				WithEmailRetriever(mockEmailRetriever),
			},
			wantErr:            false,
			wantIpType:         PUBLIC,
			wantEmailRetriever: mockEmailRetriever,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			cfg, err := applyEngineOptions(tc.opts)
			if tc.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
				assert.Equal(t, tc.wantIpType, cfg.ipType)
				assert.NotNil(t, cfg.emailRetriever)
				assert.Equal(t, fmt.Sprintf("%p", tc.wantEmailRetriever), fmt.Sprintf("%p", cfg.emailRetriever))
			}
		})
	}
}

func TestGetUser(t *testing.T) {
	testCases := []struct {
		name               string
		cfg                engineConfig
		wantUser           string
		wantIAMAuth        bool
		wantErr            bool
		mockEmailRetriever EmailRetriever
	}{
		{
			name: "user and password provided",
			cfg: engineConfig{
				user:     "testuser",
				password: "testpassword",
			},
			wantUser:    "testuser",
			wantIAMAuth: false,
			wantErr:     false,
		},
		{
			name: "iam account email provided",
			cfg: engineConfig{
				iamAccountEmail: "iam@example.com",
			},
			wantUser:    "iam@example.com",
			wantIAMAuth: true,
			wantErr:     false,
		},
		{
			name: "retrieve service account email success",
			cfg: engineConfig{
				emailRetriever: func(ctx context.Context) (string, error) {
					return "service@example.com", nil
				},
			},
			wantUser:    "service@example.com",
			wantIAMAuth: true,
			wantErr:     false,
		},
		{
			name: "retrieve service account email failure",
			cfg: engineConfig{
				emailRetriever: func(ctx context.Context) (string, error) {
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
