# pgvector retriever template

You can use PostgreSQL and `pgvector` as your retriever implementation. Use the
following examples as a starting point and modify it to work with your database
schema.

We use [database/sql](https://pkg.go.dev/database/sql) to connect to the Postgres server, but you may use another client library of your choice.

```golang
{% includecode github_path="firebase/genkit/go/samples/pgvector/main.go" region_tag="retr" adjust_indentation="auto" %}
```

And here's how to use the retriever in a flow:

```golang
{% includecode github_path="firebase/genkit/go/samples/pgvector/main.go" region_tag="use-retr" adjust_indentation="auto" %}
```
