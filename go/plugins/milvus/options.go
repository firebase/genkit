package milvus

import "google.golang.org/grpc"

// Option configures the MilvusEngine during construction.
// Multiple options can be provided to NewMilvusEngine to customize
// the underlying Milvus client connection.
type Option func(p *engineConfig)

// engineConfig holds configuration accumulated from provided Options.
// It is internal to the package and not exported.
type engineConfig struct {
	// address is the Milvus server address, e.g. "localhost:19530".
	address string
	// username used for Milvus authentication (optional).
	username string
	// password used for Milvus authentication (optional).
	password string
	// dbName selects a logical database within Milvus (optional).
	dbName string
	// enableTlsAuth enables TLS authentication when true.
	enableTlsAuth bool
	// apiKey carries API key for managed Milvus services (optional).
	apiKey string
	// dialOptions are gRPC dial options passed to the client.
	dialOptions []grpc.DialOption
	// disableConn prevents establishing the connection on creation (testing).
	disableConn bool
	// serverVersion hints the expected server version (optional).
	serverVersion string
}

// WithAddress sets the Milvus server address to connect to.
func WithAddress(address string) Option {
	return func(p *engineConfig) {
		p.address = address
	}
}

// WithUsername sets the username for Milvus authentication.
func WithUsername(username string) Option {
	return func(p *engineConfig) {
		p.username = username
	}
}

// WithPassword sets the password for Milvus authentication.
func WithPassword(password string) Option {
	return func(p *engineConfig) {
		p.password = password
	}
}

// WithDbName sets the Milvus database name to use.
func WithDbName(dbName string) Option {
	return func(p *engineConfig) {
		p.dbName = dbName
	}
}

// WithEnableTlsAuth toggles TLS authentication against the Milvus server.
func WithEnableTlsAuth(enableTlsAuth bool) Option {
	return func(p *engineConfig) {
		p.enableTlsAuth = enableTlsAuth
	}
}

// WithApiKey sets an API key for Milvus deployments that require it.
func WithApiKey(apiKey string) Option {
	return func(p *engineConfig) {
		p.apiKey = apiKey
	}
}

// WithDialOptions appends custom gRPC dial options for the client connection.
func WithDialOptions(dialOptions ...grpc.DialOption) Option {
	return func(p *engineConfig) {
		p.dialOptions = dialOptions
	}
}

// WithDisableConn prevents establishing the network connection on engine creation.
// This can be useful in tests where a real Milvus server is not available.
func WithDisableConn(disableConn bool) Option {
	return func(p *engineConfig) {
		p.disableConn = disableConn
	}
}

// WithServerVersion specifies the expected Milvus server version.
func WithServerVersion(serverVersion string) Option {
	return func(p *engineConfig) {
		p.serverVersion = serverVersion
	}
}
