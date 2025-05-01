package postgresql

type VectorStore struct {
	tableName          string
	schemaName         string
	idColumn           string
	metadataJsonColumn string
	contentColumn      string
	embeddingColumn    string
	metadataColumns    []string
}

type VectorStoresOption func(vs *VectorStore)

// WithSchemaName sets the VectorStore's schemaName field.
func WithSchemaName(schemaName string) VectorStoresOption {
	return func(v *VectorStore) {
		v.schemaName = schemaName
	}
}

// WithTableName sets the VectorStore's tableName field.
func WithTableName(tableName string) VectorStoresOption {
	return func(v *VectorStore) {
		v.tableName = tableName
	}
}

// WithContentColumn sets VectorStore's the idColumn field.
func WithIDColumn(idColumn string) VectorStoresOption {
	return func(v *VectorStore) {
		v.idColumn = idColumn
	}
}

// WithMetadataJsonColumn sets VectorStore's the metadataJsonColumn field.
func WithMetadataJsonColumn(metadataJsonColumn string) VectorStoresOption {
	return func(v *VectorStore) {
		v.metadataJsonColumn = metadataJsonColumn
	}
}

// WithContentColumn sets the VectorStore's ContentColumn field.
func WithContentColumn(contentColumn string) VectorStoresOption {
	return func(v *VectorStore) {
		v.contentColumn = contentColumn
	}
}

// WithEmbeddingColumn sets the EmbeddingColumn field.
func WithEmbeddingColumn(embeddingColumn string) VectorStoresOption {
	return func(v *VectorStore) {
		v.embeddingColumn = embeddingColumn
	}
}

// WithMetadataColumns sets the VectorStore's MetadataColumns field.
func WithMetadataColumns(metadataColumns []string) VectorStoresOption {
	return func(v *VectorStore) {
		v.metadataColumns = metadataColumns
	}
}

/*
// WithCount sets the number of Documents to return from the VectorStore.
func WithCount(count int) VectorStoresOption {
	return func(v *VectorStore) {
		v.count = count
	}
}

// WithDistanceStrategy sets the distance strategy used by the VectorStore.
func WithDistanceStrategy(distanceStrategy DistanceStrategy) VectorStoresOption {
	return func(v *VectorStore) {
		v.distanceStrategy = distanceStrategy
	}
}
*/

func NewVectorStore(opts ...VectorStoresOption) (*VectorStore, error) {
	vs := &VectorStore{
		tableName:          defaultTable,
		schemaName:         defaultSchemaName,
		idColumn:           defaultIDColumn,
		metadataJsonColumn: defaultMetadataJsonColumn,
		contentColumn:      defaultContentColumn,
		embeddingColumn:    defaultEmbeddingColumn,
	}
	vs.applyOptions(opts)
	return vs, nil
}

func (vs *VectorStore) applyOptions(opts []VectorStoresOption) {
	for _, opt := range opts {
		opt(vs)
	}
}
