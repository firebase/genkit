module github.com/firebase/genkit/go

go 1.24.0

retract (
	v0.1.4 // Retraction only.
	v0.1.3 // This shold have been a minor release.
)

require (
	cloud.google.com/go/aiplatform v1.68.0
	cloud.google.com/go/firestore v1.16.0
	cloud.google.com/go/logging v1.11.0
	cloud.google.com/go/vertexai v0.12.1-0.20240711230438-265963bd5b91
	firebase.google.com/go/v4 v4.14.1
	github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/metric v0.46.0
	github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace v1.22.0
	github.com/aymerick/raymond v2.0.2+incompatible
	github.com/google/generative-ai-go v0.16.1-0.20240711222609-09946422abc6
	github.com/google/go-cmp v0.6.0
	github.com/invopop/jsonschema v0.12.0
	github.com/jba/slog v0.2.0
	github.com/lib/pq v1.10.9
	github.com/pgvector/pgvector-go v0.2.0
	github.com/weaviate/weaviate v1.26.0-rc.1
	github.com/weaviate/weaviate-go-client/v4 v4.15.0
	github.com/wk8/go-ordered-map/v2 v2.1.8
	github.com/xeipuuv/gojsonschema v1.2.0
	go.opentelemetry.io/otel v1.29.0
	go.opentelemetry.io/otel/metric v1.29.0
	go.opentelemetry.io/otel/sdk v1.29.0
	go.opentelemetry.io/otel/sdk/metric v1.29.0
	go.opentelemetry.io/otel/trace v1.29.0
	golang.org/x/exp v0.0.0-20240318143956-a85f2c67cd81
	golang.org/x/tools v0.23.0
	google.golang.org/api v0.196.0
	google.golang.org/protobuf v1.34.2
	gopkg.in/yaml.v2 v2.4.0
	gopkg.in/yaml.v3 v3.0.1
)

require (
	cloud.google.com/go v0.115.1 // indirect
	cloud.google.com/go/ai v0.8.1-0.20240711230438-265963bd5b91 // indirect
	cloud.google.com/go/auth v0.9.3 // indirect
	cloud.google.com/go/auth/oauth2adapt v0.2.4 // indirect
	cloud.google.com/go/compute/metadata v0.5.0 // indirect
	cloud.google.com/go/iam v1.2.0 // indirect
	cloud.google.com/go/longrunning v0.6.0 // indirect
	cloud.google.com/go/monitoring v1.21.0 // indirect
	cloud.google.com/go/storage v1.43.0 // indirect
	cloud.google.com/go/trace v1.11.0 // indirect
	github.com/GoogleCloudPlatform/opentelemetry-operations-go/internal/resourcemapping v0.46.0 // indirect
	github.com/MicahParks/keyfunc v1.9.0 // indirect
	github.com/PuerkitoBio/purell v1.1.1 // indirect
	github.com/PuerkitoBio/urlesc v0.0.0-20170810143723-de5bf2ad4578 // indirect
	github.com/asaskevich/govalidator v0.0.0-20230301143203-a9d515a09cc2 // indirect
	github.com/bahlo/generic-list-go v0.2.0 // indirect
	github.com/buger/jsonparser v1.1.1 // indirect
	github.com/felixge/httpsnoop v1.0.4 // indirect
	github.com/go-logr/logr v1.4.2 // indirect
	github.com/go-logr/stdr v1.2.2 // indirect
	github.com/go-openapi/analysis v0.21.2 // indirect
	github.com/go-openapi/errors v0.22.0 // indirect
	github.com/go-openapi/jsonpointer v0.19.5 // indirect
	github.com/go-openapi/jsonreference v0.19.6 // indirect
	github.com/go-openapi/loads v0.21.1 // indirect
	github.com/go-openapi/spec v0.20.4 // indirect
	github.com/go-openapi/strfmt v0.23.0 // indirect
	github.com/go-openapi/swag v0.22.3 // indirect
	github.com/go-openapi/validate v0.21.0 // indirect
	github.com/golang-jwt/jwt/v4 v4.5.0 // indirect
	github.com/golang/groupcache v0.0.0-20210331224755-41bb18bfe9da // indirect
	github.com/golang/protobuf v1.5.4 // indirect
	github.com/google/s2a-go v0.1.8 // indirect
	github.com/google/uuid v1.6.0 // indirect
	github.com/googleapis/enterprise-certificate-proxy v0.3.3 // indirect
	github.com/googleapis/gax-go/v2 v2.13.0 // indirect
	github.com/josharian/intern v1.0.0 // indirect
	github.com/mailru/easyjson v0.7.7 // indirect
	github.com/mitchellh/mapstructure v1.5.0 // indirect
	github.com/oklog/ulid v1.3.1 // indirect
	github.com/pkg/errors v0.9.1 // indirect
	github.com/xeipuuv/gojsonpointer v0.0.0-20190905194746-02993c407bfb // indirect
	github.com/xeipuuv/gojsonreference v0.0.0-20180127040603-bd5ef7bd5415 // indirect
	go.mongodb.org/mongo-driver v1.14.0 // indirect
	go.opencensus.io v0.24.0 // indirect
	go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc v0.54.0 // indirect
	go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp v0.54.0 // indirect
	golang.org/x/crypto v0.26.0 // indirect
	golang.org/x/net v0.28.0 // indirect
	golang.org/x/oauth2 v0.22.0 // indirect
	golang.org/x/sync v0.8.0 // indirect
	golang.org/x/sys v0.24.0 // indirect
	golang.org/x/text v0.17.0 // indirect
	golang.org/x/time v0.6.0 // indirect
	google.golang.org/appengine/v2 v2.0.2 // indirect
	google.golang.org/genproto v0.0.0-20240903143218-8af14fe29dc1 // indirect
	google.golang.org/genproto/googleapis/api v0.0.0-20240903143218-8af14fe29dc1 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20240903143218-8af14fe29dc1 // indirect
	google.golang.org/grpc v1.66.0 // indirect
)
