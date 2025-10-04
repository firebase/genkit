# Beta API Design Recommendations for Code Execution

## Current Implementation Analysis

The current auto-enabling design has both strengths and weaknesses:

### ✅ **Good Design Elements:**
- Explicit `useBetaAPI` flag takes precedence over auto-detection
- Clear separation between regular and Beta API request handling
- Graceful fallback mechanisms

### ❌ **Design Issues:**
- Hard-coded beta header `"code-execution-2025-08-25"`
- Auto-enabling based on feature flags may break when features graduate
- Tight coupling between feature availability and API version

## Recommended Improvements

### 1. **Version-Aware Configuration**

```go
// Enhanced configuration structure
type AnthropicUIConfig struct {
    // ... existing fields ...
    
    // Code Execution configuration
    CodeExecutionEnabled bool   `json:"codeExecutionEnabled"`
    CodeExecutionVersion string `json:"codeExecutionVersion,omitempty"` // "beta", "stable", "auto"
    
    // Beta API configuration
    UseBetaAPI     bool     `json:"useBetaAPI"`
    BetaFeatures   []string `json:"betaFeatures,omitempty"` // ["code-execution-2025-08-25"]
}
```

### 2. **Feature-to-API Mapping**

```go
// Feature availability mapping
var featureAPIMapping = map[string]APIRequirement{
    "code_execution": {
        BetaVersion:   "code-execution-2025-08-25",
        StableVersion: "", // Empty until graduated
        RequiresBeta:  true,
    },
    "web_search": {
        BetaVersion:   "web-search-2025-03-05", 
        StableVersion: "web-search-stable",
        RequiresBeta:  false, // Available in both
    },
}

type APIRequirement struct {
    BetaVersion   string
    StableVersion string
    RequiresBeta  bool
}
```

### 3. **Improved Beta Detection Logic**

```go
func isBetaApiEnabled(config any) bool {
    if mapConfig, ok := config.(map[string]any); ok {
        // 1. Explicit useBetaAPI flag always takes precedence
        if useBetaAPI, exists := mapConfig["useBetaAPI"]; exists {
            if enabled, ok := useBetaAPI.(bool); ok {
                return enabled
            }
        }
        
        // 2. Check if any enabled features require Beta API
        return hasFeatureRequiringBeta(mapConfig)
    }
    return false
}

func hasFeatureRequiringBeta(config map[string]any) bool {
    // Check code execution
    if codeEnabled, exists := config["codeExecutionEnabled"]; exists {
        if enabled, ok := codeEnabled.(bool); ok && enabled {
            version := getCodeExecutionVersion(config)
            if version == "beta" || (version == "auto" && requiresBetaForCodeExecution()) {
                return true
            }
        }
    }
    
    // Check other beta features...
    return false
}

func requiresBetaForCodeExecution() bool {
    // This function encapsulates the logic for determining if code execution
    // currently requires Beta API. When it graduates, this returns false.
    return featureAPIMapping["code_execution"].RequiresBeta
}
```

### 4. **Dynamic Header Management**

```go
func getBetaHeaders(config map[string]any) []string {
    var headers []string
    
    // Add headers based on enabled features
    if isCodeExecutionEnabled(config) && requiresBetaForCodeExecution() {
        headers = append(headers, featureAPIMapping["code_execution"].BetaVersion)
    }
    
    // Add other feature headers...
    return headers
}

func createBetaClient(baseClient anthropic.Client, config map[string]any) anthropic.Client {
    headers := getBetaHeaders(config)
    if len(headers) == 0 {
        return baseClient // No beta features needed
    }
    
    return anthropic.NewClient(
        option.WithAPIKey(os.Getenv("ANTHROPIC_API_KEY")),
        option.WithHeader("anthropic-beta", strings.Join(headers, ",")),
    )
}
```

### 5. **Migration Strategy**

```go
// Migration helper for when features graduate
func getAPIClientForFeature(feature string, baseClient anthropic.Client, config map[string]any) (anthropic.Client, bool) {
    mapping, exists := featureAPIMapping[feature]
    if !exists {
        return baseClient, false // Feature not found
    }
    
    version := getFeatureVersion(feature, config)
    
    switch version {
    case "stable":
        if mapping.StableVersion != "" {
            return baseClient, false // Use regular API
        }
        fallthrough // Stable not available, use beta
    case "beta", "auto":
        if mapping.RequiresBeta {
            betaClient := createBetaClient(baseClient, config)
            return betaClient, true // Use Beta API
        }
        return baseClient, false // Feature available in regular API
    default:
        return baseClient, false
    }
}
```

## Benefits of This Approach

### 1. **Future-Proof Design**
- Features can graduate from Beta without breaking existing code
- Version selection allows gradual migration
- Clear separation of concerns

### 2. **Explicit Control**
- Users can explicitly choose API versions
- `useBetaAPI` flag provides override capability
- Feature-specific version control

### 3. **Backward Compatibility**
- Current behavior preserved with `codeExecutionEnabled: true`
- Gradual migration path when features graduate
- No breaking changes for existing users

### 4. **Maintainability**
- Centralized feature-to-API mapping
- Easy to update when new features are added
- Clear upgrade path for beta headers

## Implementation Priority

### Phase 1: **Immediate (Low Risk)**
- Add `featureAPIMapping` configuration
- Implement dynamic header generation
- Maintain current auto-enabling behavior

### Phase 2: **Medium Term (Preparation)**
- Add version-aware configuration options
- Implement feature-specific API client selection
- Add migration helpers

### Phase 3: **Future (When Features Graduate)**
- Update feature mappings
- Provide migration documentation
- Deprecate old auto-enabling logic

## Conclusion

The current implementation is **functional but not future-proof**. The recommended improvements provide:

1. **Graceful migration** when Code Execution graduates from Beta
2. **Explicit control** over API version selection
3. **Backward compatibility** for existing applications
4. **Maintainable architecture** for future beta features

**Recommendation**: Implement Phase 1 improvements now to prepare for future API changes while maintaining current functionality.