#!/bin/bash
# Run the Google GenAI sample application with Genkit Dev UI
cd "$(dirname "$0")"
mvn exec:java -Dexec.mainClass="com.google.genkit.samples.GoogleGenAIApp" -q
