package postgresql

import (
	"fmt"
	"strconv"
	"strings"
)

// SimilaritySearchOption option for SimilaritySearch
type SimilaritySearchOption func(vs *SimilaritySearch)

type SimilaritySearch struct {
	VectorStore

	/*tableName          string
	schemaName         string
	idColumn           string
	metadataJsonColumn string
	contentColumn      string
	embeddingColumn    string
	metadataColumns    []string
	*/
	filter           any
	k                int
	distanceStrategy DistanceStrategy
}

/*
// WithSchemaName sets the SimilaritySearch's schemaName field.
func WithSchemaName(schemaName string) SimilaritySearchOption {
	return func(v *SimilaritySearch) {
		v.schemaName = schemaName
	}
}

// WithTableName sets the SimilaritySearch's tableName field.
func WithTableName(tableName string) SimilaritySearchOption {
	return func(v *SimilaritySearch) {
		v.tableName = tableName
	}
}

// WithIDColumn sets SimilaritySearch's the idColumn field.
func WithIDColumn(idColumn string) SimilaritySearchOption {
	return func(v *SimilaritySearch) {
		v.idColumn = idColumn
	}
}

// WithMetadataJsonColumn sets SimilaritySearch's the metadataJsonColumn field.
func WithMetadataJsonColumn(metadataJsonColumn string) SimilaritySearchOption {
	return func(v *SimilaritySearch) {
		v.metadataJsonColumn = metadataJsonColumn
	}
}

// WithContentColumn sets the SimilaritySearch's ContentColumn field.
func WithContentColumn(contentColumn string) SimilaritySearchOption {
	return func(v *SimilaritySearch) {
		v.contentColumn = contentColumn
	}
}

// WithEmbeddingColumn sets the EmbeddingColumn field.
func WithEmbeddingColumn(embeddingColumn string) SimilaritySearchOption {
	return func(v *SimilaritySearch) {
		v.embeddingColumn = embeddingColumn
	}
}

// WithMetadataColumns sets the SimilaritySearch's MetadataColumns field.
func WithMetadataColumns(metadataColumns []string) SimilaritySearchOption {
	return func(v *SimilaritySearch) {
		v.metadataColumns = metadataColumns
	}
}
*/

// WithCount sets the number of Documents to return from the SimilaritySearch.
func WithCount(count int) SimilaritySearchOption {
	return func(v *SimilaritySearch) {
		v.k = count
	}
}

// WithDistanceStrategy sets the distance strategy used by the SimilaritySearch.
func WithDistanceStrategy(distanceStrategy DistanceStrategy) SimilaritySearchOption {
	return func(v *SimilaritySearch) {
		v.distanceStrategy = distanceStrategy
	}
}

// WithFilter sets the filter used by the SimilaritySearch.
func WithFilter(filter string) SimilaritySearchOption {
	return func(v *SimilaritySearch) {
		v.filter = filter
	}
}

func NewSimilaritySearch(opts ...SimilaritySearchOption) *SimilaritySearch {
	vs := &SimilaritySearch{
		VectorStore: VectorStore{
			tableName:          defaultTable,
			schemaName:         defaultSchemaName,
			idColumn:           defaultIDColumn,
			metadataJsonColumn: defaultMetadataJsonColumn,
			contentColumn:      defaultContentColumn,
			embeddingColumn:    defaultEmbeddingColumn,
		},
		k:                defaultCount,
		distanceStrategy: defaultDistanceStrategy,
	}
	vs.applyOptions(opts)
	return vs
}

func (ss *SimilaritySearch) applyOptions(opts []SimilaritySearchOption) {
	for _, opt := range opts {
		opt(ss)
	}
}

func (ss *SimilaritySearch) buildQuery(embedding []float32) string {

	vectorToString := func(v []float32) string {
		stringArray := make([]string, len(v))
		for i, val := range v {
			stringArray[i] = strconv.FormatFloat(float64(val), 'f', -1, 32)
		}
		return "[" + strings.Join(stringArray, ", ") + "]"
	}

	operator := ss.distanceStrategy.operator()
	searchFunction := ss.distanceStrategy.similaritySearchFunction()
	columns := append(ss.metadataColumns, ss.contentColumn)
	if ss.metadataJsonColumn != "" {
		columns = append(columns, ss.metadataJsonColumn)
	}
	columnNames := strings.Join(columns, `, `)
	whereClause := ""
	if ss.filter != nil {
		whereClause = fmt.Sprintf("WHERE %s", ss.filter)
	}
	stmt := fmt.Sprintf(`
        SELECT %s, %s(%s, '%s') AS distance FROM "%s"."%s" %s ORDER BY %s %s '%s' LIMIT %d;`,
		columnNames, searchFunction, ss.embeddingColumn, vectorToString(embedding), ss.schemaName, ss.tableName,
		whereClause, ss.embeddingColumn, operator, vectorToString(embedding), ss.k)

	return stmt
}
