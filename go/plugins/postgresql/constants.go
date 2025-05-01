package postgresql

const (
	defaultSchemaName         = "public"
	defaultIDColumn           = "id"
	defaultContentColumn      = "content"
	defaultEmbeddingColumn    = "embedding"
	defaultMetadataJsonColumn = "metadata"
	defaultCount              = 4
	defaultTable              = "embeddings"
	defaultUserAgent          = "genkit-cloud-sql-pg-go/0.0.0"
)

// defaultDistanceStrategy is the default strategy used if none is provided.
var defaultDistanceStrategy = CosineDistance{}
