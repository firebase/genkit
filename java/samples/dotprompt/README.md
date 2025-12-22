# Genkit DotPrompt Sample

This sample demonstrates how to use DotPrompt files with Genkit Java for building AI applications with complex inputs and outputs.

## Features Demonstrated

- **DotPrompt Files**: Load and use `.prompt` files with Handlebars templating
- **Complex Input Schemas**: Handle nested objects, arrays, and optional fields
- **Complex Output Schemas**: Parse structured JSON responses into Java objects
- **Prompt Variants**: Use different prompt variations (e.g., `recipe.robot.prompt`)
- **Partials**: Include reusable template fragments (e.g., `_style.prompt`)

## Prompt Files

Located in `src/main/resources/prompts/`:

- `recipe.prompt` - Generate recipes with structured output
- `recipe.robot.prompt` - Robot-themed recipe generation
- `story.prompt` - Story generation with personality options
- `travel-planner.prompt` - Complex travel itinerary generation
- `code-review.prompt` - Code analysis with detailed output
- `_style.prompt` - Partial template for personality styling

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
cd java/samples/dotprompt

# Run the sample
./run.sh
# Or: mvn compile exec:java
```

### Option 2: With Genkit Dev UI (Recommended)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/dotprompt

# Run with Genkit CLI
genkit start -- ./run.sh
```

The Dev UI will be available at http://localhost:4000

## Example API Calls

### Generate a Recipe
```bash
curl -X POST http://localhost:8080/chefFlow \
  -H 'Content-Type: application/json' \
  -d '{"food":"pasta carbonara","ingredients":["bacon","eggs","parmesan"]}'
```

### Robot Chef Recipe
```bash
curl -X POST http://localhost:8080/robotChefFlow \
  -H 'Content-Type: application/json' \
  -d '{"food":"pizza"}'
```

### Tell a Story
```bash
curl -X POST http://localhost:8080/tellStory \
  -H 'Content-Type: application/json' \
  -d '{"subject":"a brave knight","personality":"dramatic","length":"short"}'
```

### Plan a Trip
```bash
curl -X POST http://localhost:8080/planTrip \
  -H 'Content-Type: application/json' \
  -d '{
    "destination": "Tokyo",
    "duration": 5,
    "budget": "$3000",
    "interests": ["food", "culture", "technology"],
    "travelStyle": "adventure"
  }'
```

### Code Review
```bash
curl -X POST http://localhost:8080/reviewCode \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "function add(a, b) { return a + b; }",
    "language": "javascript",
    "analysisType": "best practices"
  }'
```

## Output Schemas

### Recipe
```json
{
  "title": "Pasta Carbonara",
  "ingredients": [
    {"name": "spaghetti", "quantity": "400g"},
    {"name": "bacon", "quantity": "200g"}
  ],
  "steps": ["Step 1...", "Step 2..."],
  "prepTime": "10 minutes",
  "cookTime": "20 minutes",
  "servings": 4
}
```

### Travel Itinerary
```json
{
  "tripName": "Tokyo Adventure",
  "destination": "Tokyo",
  "duration": 5,
  "dailyItinerary": [
    {
      "day": 1,
      "title": "Arrival & Exploration",
      "activities": [
        {
          "time": "9:00 AM",
          "activity": "Visit Senso-ji Temple",
          "location": "Asakusa",
          "estimatedCost": "$10",
          "tips": "Go early to avoid crowds"
        }
      ]
    }
  ],
  "estimatedBudget": {
    "accommodation": "$800",
    "food": "$500",
    "activities": "$400",
    "transportation": "$300",
    "total": "$2000"
  },
  "packingList": ["Comfortable shoes", "Power adapter"],
  "travelTips": ["Get a JR Pass", "Learn basic Japanese phrases"]
}
```

## Development UI

Access the Genkit Development UI at http://localhost:3100 to:
- Browse available flows and prompts
- Test flows interactively
- View execution traces
