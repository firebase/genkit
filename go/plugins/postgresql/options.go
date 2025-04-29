package postgresql

import (
	"github.com/jackc/pgx/v5/pgxpool"
)

const (
	defaultSchemaName = "public"
	defaultUserAgent  = "genkit-cloud-sql-pg-go/0.0.0"
)

// Option is a function type that can be used to modify the Engine.
type Option func(p *engineConfig)

type engineConfig struct {
	projectID       string
	region          string
	instance        string
	connPool        *pgxpool.Pool
	database        string
	user            string
	password        string
	ipType          IpType
	iamAccountEmail string
	userAgents      string
}

// WithCloudSQLInstance sets the project, region, and instance fields.
func WithCloudSQLInstance(projectID, region, instance string) Option {
	return func(p *engineConfig) {
		p.projectID = projectID
		p.region = region
		p.instance = instance
	}
}

// WithPool sets the Port field.
func WithPool(pool *pgxpool.Pool) Option {
	return func(p *engineConfig) {
		p.connPool = pool
	}
}

// WithDatabase sets the Database field.
func WithDatabase(database string) Option {
	return func(p *engineConfig) {
		p.database = database
	}
}

// WithUser sets the User field.
func WithUser(user string) Option {
	return func(p *engineConfig) {
		p.user = user
	}
}

// WithPassword sets the Password field.
func WithPassword(password string) Option {
	return func(p *engineConfig) {
		p.password = password
	}
}

// WithIPType sets the IpType field.
func WithIPType(ipType IpType) Option {
	return func(p *engineConfig) {
		p.ipType = ipType
	}
}

// WithIAMAccountEmail sets the IAMAccountEmail field.
func WithIAMAccountEmail(email string) Option {
	return func(p *engineConfig) {
		p.iamAccountEmail = email
	}
}
