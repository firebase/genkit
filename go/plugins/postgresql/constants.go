package postgresql

const (
	defaultSchemaName         = "public"
	defaultIDColumn           = "id"
	defaultContentColumn      = "content"
	defaultEmbeddingColumn    = "embedding"
	defaultMetadataJsonColumn = "metadata"
	defaultCount              = 4
	defaultUserAgent          = "genkit-cloud-sql-pg-go/0.0.0"
	defaultIndexNameSuffix    = "vectorindex"
)

// defaultDistanceStrategy is the default strategy used if none is provided.
var defaultDistanceStrategy = CosineDistance{}
