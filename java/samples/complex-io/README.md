# Complex I/O Sample

This sample demonstrates working with complex input and output types in Genkit Java flows.

## Overview

The sample showcases:

- **Deeply nested object types** - OrderRequest with Customer, Address, PaymentMethod nested objects
- **Arrays and collections** - Lists of OrderItems, TimelineEvents, Recommendations
- **Optional fields** - Various nullable fields throughout the types
- **Maps and generic types** - Metadata maps, dynamic aggregation results
- **Complex domain objects** - E-commerce orders, analytics dashboards

## Complex Types

### OrderRequest / OrderResponse
Simulates a complex e-commerce order with:
- Customer information with preferences
- Multiple order items with customizations
- Shipping and billing addresses with coordinates
- Payment method details
- Metadata maps

### AnalyticsRequest / AnalyticsResponse
Simulates a complex analytics dashboard query with:
- Date ranges with timezone support
- Nested filters with logical operators
- Multiple grouping and aggregation options
- Sorting and pagination
- Visualizations with chart configurations
- AI-generated insights with suggested actions

### ValidationResult
Demonstrates validation output with:
- List of errors with field paths
- List of warnings
- Severity levels

## Available Flows

| Flow | Input | Output | Description |
|------|-------|--------|-------------|
| `processOrder` | OrderRequest | OrderResponse | Process complex order and return detailed response |
| `generateAnalytics` | AnalyticsRequest | AnalyticsResponse | Generate analytics dashboard data |
| `processBatch` | List<String> | Map<String, Object> | Process batch of items |
| `simplifyOrder` | OrderRequest | Map<String, Object> | Transform order to simplified format |
| `validateOrder` | OrderRequest | ValidationResult | Validate order structure |

## Prerequisites

- Java 17+
- Maven 3.6+
- OpenAI API key

## Running the Sample

### Option 1: Direct Run

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/complex-io

# Run the sample
./run.sh
# Or: mvn compile exec:java
```

### Option 2: With Genkit Dev UI (Recommended)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/complex-io

# Run with Genkit CLI
genkit start -- ./run.sh
```

The Dev UI will be available at http://localhost:4000

## Example Requests

### Process Order

```bash
curl -X POST http://localhost:8080/api/flow/processOrder \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "CUST-001",
    "customer": {
      "id": "CUST-001",
      "firstName": "John",
      "lastName": "Doe",
      "email": "john@example.com",
      "phone": "+1-555-123-4567",
      "preferences": {
        "communicationChannel": "email",
        "marketingOptIn": true,
        "language": "en"
      }
    },
    "items": [
      {
        "productId": "PROD-001",
        "name": "Wireless Mouse",
        "quantity": 2,
        "unitPrice": 29.99,
        "customizations": [
          {
            "type": "color",
            "value": "black",
            "additionalCost": 0
          }
        ]
      },
      {
        "productId": "PROD-002",
        "name": "USB-C Hub",
        "quantity": 1,
        "unitPrice": 49.99
      }
    ],
    "shippingAddress": {
      "street1": "123 Main St",
      "street2": "Apt 4B",
      "city": "San Francisco",
      "state": "CA",
      "postalCode": "94102",
      "country": "USA",
      "coordinates": {
        "latitude": 37.7749,
        "longitude": -122.4194
      }
    },
    "billingAddress": {
      "street1": "123 Main St",
      "city": "San Francisco",
      "state": "CA",
      "postalCode": "94102",
      "country": "USA"
    },
    "paymentMethod": {
      "type": "credit_card",
      "details": {
        "lastFourDigits": "4242",
        "cardType": "visa",
        "expirationMonth": 12,
        "expirationYear": 2026
      }
    },
    "orderNotes": "Please leave at door",
    "metadata": {
      "source": "web",
      "campaign": "winter-sale"
    }
  }'
```

### Generate Analytics

```bash
curl -X POST http://localhost:8080/api/flow/generateAnalytics \
  -H "Content-Type: application/json" \
  -d '{
    "dashboardId": "sales-overview",
    "dateRange": {
      "start": "2025-01-01",
      "end": "2025-02-10",
      "timezone": "America/Los_Angeles",
      "preset": "last_30_days"
    },
    "filters": [
      {
        "field": "status",
        "operator": "eq",
        "value": "completed"
      },
      {
        "field": "amount",
        "operator": "gte",
        "value": 100
      }
    ],
    "groupBy": [
      {
        "field": "created_at",
        "interval": "day",
        "alias": "date"
      }
    ],
    "metrics": [
      {
        "name": "Total Revenue",
        "field": "amount",
        "aggregation": "sum",
        "format": "currency"
      },
      {
        "name": "Order Count",
        "field": "id",
        "aggregation": "count",
        "format": "number"
      }
    ],
    "sorting": [
      {
        "field": "date",
        "direction": "desc"
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 50
    }
  }'
```

### Validate Order

```bash
curl -X POST http://localhost:8080/api/flow/validateOrder \
  -H "Content-Type: application/json" \
  -d '{
    "items": []
  }'
```

This will return validation errors because required fields are missing.

## Type Hierarchy

```
OrderRequest
├── Customer
│   └── CustomerPreferences
├── List<OrderItem>
│   ├── Discount
│   └── List<Customization>
├── Address (shipping)
│   └── Coordinates
├── Address (billing)
├── PaymentMethod
│   └── PaymentDetails
└── Map<String, Object> (metadata)

OrderResponse
├── CustomerSummary
├── OrderSummary
│   ├── List<ProcessedItem>
│   ├── MoneyAmount (subtotal, shipping, total)
│   ├── List<AppliedDiscount>
│   │   └── MoneyAmount
│   └── TaxInfo
│       └── List<TaxBreakdown>
│           └── MoneyAmount
├── ShippingInfo
│   ├── DateRange
│   └── FormattedAddress
├── PaymentInfo
│   └── FormattedAddress
├── List<TimelineEvent>
├── List<Recommendation>
│   └── MoneyAmount
└── OrderAnalytics
    └── MoneyAmount
```

## Use Cases

This sample is useful for testing:

1. **Schema Generation** - How Genkit generates JSON schemas for complex nested types
2. **Serialization** - Jackson serialization/deserialization of deeply nested objects
3. **Type Safety** - Java generics handling with flows
4. **Validation** - Input validation with complex structures
5. **UI Rendering** - Testing Genkit Developer UI with complex types
