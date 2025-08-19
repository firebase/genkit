#!/bin/bash

# Script to fix genkit.Init usage across the Go codebase

echo "Fixing genkit.Init usage patterns..."

# Find all .go files that have the old pattern and fix them
find . -name "*.go" -type f -exec grep -l "g, err := genkit\.Init" {} \; | while read file; do
    echo "Fixing $file..."
    
    # Fix the assignment pattern - handle multi-line cases
    sed -i.bak -E '/g, err := genkit\.Init/{
        N
        N
        N
        N
        N
        s/g, err := genkit\.Init([^)]*\))\n[[:space:]]*if err != nil \{[[:space:]]*\n[[:space:]]*log\.Fatal[^}]*\}/g := genkit.Init\1/
    }' "$file"
    
    # Simpler pattern for single line cases
    sed -i.bak2 's/g, err := genkit\.Init(/g := genkit.Init(/g' "$file"
    
    # Remove unused log imports if the file no longer has log.Fatal calls
    if ! grep -q "log\." "$file"; then
        sed -i.bak3 '/^[[:space:]]*"log"[[:space:]]*$/d' "$file"
    fi
    
    # Clean up backup files
    rm -f "$file.bak" "$file.bak2" "$file.bak3"
done

echo "Done!"