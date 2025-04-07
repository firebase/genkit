package postgres

type DistanceStrategy interface {
	String() string
	operator() string
	searchFunction() string
	similaritySearchFunction() string
}

type Euclidean struct{}

func (e Euclidean) String() string {
	return "euclidean"
}

func (e Euclidean) operator() string {
	return "<->"
}

func (e Euclidean) searchFunction() string {
	return "vector_l2_ops"
}

func (e Euclidean) similaritySearchFunction() string {
	return "l2_distance"
}

type CosineDistance struct{}

func (c CosineDistance) String() string {
	return "cosineDistance"
}

func (c CosineDistance) operator() string {
	return "<=>"
}

func (c CosineDistance) searchFunction() string {
	return "vector_cosine_ops"
}

func (c CosineDistance) similaritySearchFunction() string {
	return "cosine_distance"
}

type InnerProduct struct{}

func (i InnerProduct) String() string {
	return "innerProduct"
}

func (i InnerProduct) operator() string {
	return "<#>"
}

func (i InnerProduct) searchFunction() string {
	return "vector_ip_ops"
}

func (i InnerProduct) similaritySearchFunction() string {
	return "inner_product"
}
