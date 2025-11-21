# Firebase Genkit Issue #3280: Integrate dotprompt to Python Implementation

## Executive Summary

This document provides a comprehensive analysis and execution plan for implementing dotprompt functionality in the Python version of Firebase Genkit. The goal is to achieve feature parity with the stable JavaScript/TypeScript implementation by adding support for `.prompt` files, template processing, and file-based prompt management.

## Problem Analysis

### Issue Overview
**Issue #3280**: Integrate dotprompt standalone library to the Python project

The Firebase Genkit project supports multiple programming languages, with JavaScript/TypeScript being the stable, feature-complete implementation. The Python implementation is in early development and lacks several key features, particularly dotprompt support for file-based prompt management and templating.

### Current State Analysis

#### JavaScript/TypeScript Implementation (Stable)
-  Full dotprompt support with `.prompt` file loading and parsing
- Handlebars-based templating engine
- YAML frontmatter for metadata, model config, and schemas
- Runtime prompt compilation and execution
- Prompt variants and namespace support
- Helper functions and partials
-  Automatic prompt folder scanning

#### Python Implementation (Early Development)
- ✅ Basic `ExecutablePrompt` class exists
- ✅ Programmatic prompt definition via `define_prompt()`
- ❌ No `.prompt` file support
- ❌ No template processing capabilities
- ❌ No file-based prompt management
- ❌ TODO comment in code: "run str prompt/system/message through dotprompt using input"

### Gap Analysis

The main gaps between JavaScript and Python implementations:

1. **File Format Support**: No parsing of `.prompt` files with YAML frontmatter
2. **Template Engine**: No Handlebars-compatible templating system
3. **File Management**: No automatic loading and scanning of prompt directories
4. **Variants**: No support for prompt variants (e.g., `prompt.variant.prompt`)
5. **Helpers & Partials**: No support for reusable template components

## dotprompt Functionality Overview

### File Format Structure
```yaml
---
model: googleai/gemini-1.5-flash
config:
  temperature: 0.9
input:
  schema:
    location: string
    style?: string
    name?: string
  default:
    location: a restaurant
---

You are the world's most welcoming AI assistant and are currently working at {{location}}.

Greet a guest{{#if name}} named {{name}}{{/if}}{{#if style}} in the style of {{style}}{{/if}}.
```

### Key Features
- **YAML Frontmatter**: Model configuration, input/output schemas, metadata
- **Handlebars Templates**: Dynamic content with `{{variable}}`, `{{#if}}`, `{{#each}}`
- **File-based Management**: Organized prompt libraries in directories
- **Variants**: Multiple versions of prompts (formal, casual, etc.)
- **Helpers**: Custom template functions for advanced logic
- **Partials**: Reusable template components

## Detailed Execution Plan

### Phase 1: Core Infrastructure Setup

#### 1.1 Module Structure Creation
Create the following directory structure:
```
py/packages/genkit/src/genkit/dotprompt/
├── __init__.py          # Public API exports
├── parser.py            # YAML frontmatter + template parsing
├── template.py          # Handlebars-like templating engine
├── loader.py            # .prompt file loading and folder scanning
├── helpers.py           # Built-in template helpers
├── types.py             # Type definitions and schemas
└── exceptions.py        # Custom exception classes
```

#### 1.2 Dependencies Addition
Add to `pyproject.toml`:
```toml
dependencies = [
    "pyyaml>=6.0",           # YAML frontmatter parsing
    "pybars3>=0.9.7",        # Handlebars-compatible templating
         "pathlib",               # File system operations (built-in)
    "typing-extensions",     # Enhanced typing support
]
```

### Phase 2: Core Components Implementation

#### 2.1 Prompt File Parser (`parser.py`)
```python
class PromptFile:
    """Represents a parsed .prompt file with metadata and template."""
    
    def __init__(self, metadata: dict, template: str, file_path: str):
        self.metadata = metadata
        self.template = template
        self.file_path = file_path
        self.model = metadata.get('model')
        self.config = metadata.get('config', {})
        self.input_schema = metadata.get('input', {}).get('schema')
        self.output_schema = metadata.get('output', {}).get('schema')

class PromptParser:
    """Parses .prompt files with YAML frontmatter and template content."""
    
    def parse_file(self, file_path: str) -> PromptFile:
        """Parse a .prompt file and return PromptFile object."""
        pass
    
    def parse_content(self, content: str) -> PromptFile:
        """Parse prompt content string."""
        pass
```

#### 2.2 Template Engine (`template.py`)
```python
class CompiledTemplate:
    """A compiled template ready for rendering."""
    pass

class TemplateEngine:
    """Handlebars-compatible template processing engine."""
    
    def __init__(self):
        self.helpers = {}
        self.partials = {}
    
    def compile(self, template: str) -> CompiledTemplate:
        """Compile a template string into executable form."""
        pass
    
    def render(self, template: CompiledTemplate, context: dict) -> str:
        """Render a compiled template with given context."""
        pass
    
    def register_helper(self, name: str, helper_fn: callable):
        """Register a template helper function."""
        pass
    
    def register_partial(self, name: str, template: str):
        """Register a template partial."""
        pass
```

#### 2.3 File Loader (`loader.py`)
```python
class PromptLoader:
    """Loads and manages .prompt files from directories."""
    
    def __init__(self, template_engine: TemplateEngine):
        self.template_engine = template_engine
        self.cache = {}
    
    def load_prompt_folder(self, dir_path: str, namespace: str = '') -> dict:
        """Recursively load all .prompt files from directory."""
        pass
    
    def load_prompt_file(self, file_path: str) -> PromptFile:
        """Load a single .prompt file."""
        pass
    
    def get_prompt(self, name: str, variant: str = None) -> PromptFile:
        """Retrieve a loaded prompt by name and variant."""
        pass
```

### Phase 3: Integration with Existing Prompt System

#### 3.1 Enhance ExecutablePrompt Class
Update `py/packages/genkit/src/genkit/blocks/prompt.py`:

```python
class ExecutablePrompt:
    def __init__(self, ...):
        # Existing initialization
        self._template_engine = None
        self._prompt_file = None
    
    def render(self, input: Any | None = None, config: dict | None = None) -> GenerateActionOptions:
        """Enhanced render method with template processing."""
        # Process templates using dotprompt if string templates are provided
        processed_system = self._process_template(self._system, input)
        processed_prompt = self._process_template(self._prompt, input)
        processed_messages = self._process_messages(self._messages, input)
        
        return to_generate_action_options(
            registry=self._registry,
            model=self._model,
            prompt=processed_prompt,
            system=processed_system,
            messages=processed_messages,
            # ... rest of parameters
        )
    
    def _process_template(self, template: str | Part | list[Part] | None, input: Any) -> str | Part | list[Part] | None:
        """Process template strings with dotprompt engine."""
        if isinstance(template, str) and self._template_engine:
            compiled = self._template_engine.compile(template)
            return self._template_engine.render(compiled, input or {})
        return template
```

#### 3.2 Add New API Functions

The dotprompt API functions will be organized across multiple files and exposed through `__init__.py`:

**File Structure**:
```
py/packages/genkit/src/genkit/dotprompt/
├── __init__.py          # Public API exports and convenience functions
├── api.py               # Main API functions implementation
├── parser.py            # File parsing logic
├── template.py          # Template engine
├── loader.py            # File loading logic
└── types.py             # Type definitions
```

**`py/packages/genkit/src/genkit/dotprompt/__init__.py`**:
```python
"""Dotprompt module for file-based prompt management."""

from .api import (
    load_prompt_folder,
    define_helper,
    define_partial,
    prompt,
    create_prompt_from_file,
)
from .types import PromptFile, CompiledTemplate
from .template import TemplateEngine
from .loader import PromptLoader

# Re-export main API functions for easy importing
__all__ = [
    'load_prompt_folder',
    'define_helper', 
    'define_partial',
    'prompt',
    'create_prompt_from_file',
    'PromptFile',
    'CompiledTemplate',
    'TemplateEngine',
    'PromptLoader',
]
```

**`py/packages/genkit/src/genkit/dotprompt/api.py`**:
```python
"""Main API functions for dotprompt functionality."""

from genkit.core.registry import Registry
from genkit.blocks.prompt import ExecutablePrompt
from .loader import PromptLoader
from .types import PromptFile

def load_prompt_folder(registry: Registry, dir: str = './prompts', ns: str = ''):
    """Load all .prompt files from directory into registry."""
    loader = registry.prompt_loader
    loaded_prompts = loader.load_prompt_folder(dir, ns)
    
    for name, prompt_file in loaded_prompts.items():
        registry.register_prompt_from_file(name, prompt_file)

def define_helper(registry: Registry, name: str, fn: callable):
    """Register a template helper function."""
    registry.dotprompt.register_helper(name, fn)

def define_partial(registry: Registry, name: str, source: str):
    """Register a template partial."""
    registry.dotprompt.register_partial(name, source)

def prompt(registry: Registry, name: str, variant: str = None, dir: str = './prompts') -> ExecutablePrompt:
    """Load and return an executable prompt from .prompt file."""
    return registry.get_prompt(name, variant)

def create_prompt_from_file(registry: Registry, file_path: str) -> ExecutablePrompt:
    """Create ExecutablePrompt from .prompt file."""
    loader = registry.prompt_loader
    prompt_file = loader.load_prompt_file(file_path)
    return _create_executable_from_prompt_file(registry, prompt_file)

def _create_executable_from_prompt_file(registry: Registry, prompt_file: PromptFile) -> ExecutablePrompt:
    """Internal helper to create ExecutablePrompt from PromptFile."""
    # Implementation details...
    pass
```

**Usage Examples**:
```python
# Import the functions from the dotprompt module
from genkit.dotprompt import load_prompt_folder, define_helper, prompt

# Or import the entire module
import genkit.dotprompt as dotprompt

# Usage in application code
ai = genkit({'plugins': [google_genai()]})

# Load all prompts from directory
load_prompt_folder(ai.registry, './prompts')

# Define custom helper
define_helper(ai.registry, 'uppercase', lambda text: text.upper())

# Use a loaded prompt
greeting = prompt(ai.registry, 'greeting', variant='formal')
response = await greeting({'name': 'Alice'})
```

### Phase 4: Registry Integration

#### 4.1 Extend Registry Class
Update `py/packages/genkit/src/genkit/core/registry.py`:

```python
class Registry:
    def __init__(self):
        # Existing initialization
        self.dotprompt = TemplateEngine()
        self.prompt_loader = PromptLoader(self.dotprompt)
        self.loaded_prompts = {}
    
    def register_prompt_from_file(self, name: str, prompt_file: PromptFile):
        """Register a prompt loaded from .prompt file."""
        pass
    
    def get_prompt(self, name: str, variant: str = None) -> ExecutablePrompt:
        """Retrieve a registered prompt."""
        pass
```

#### 4.2 Auto-loading Integration
Add to main Genkit initialization:

```python
class Genkit:
    def __init__(self, options: GenkitOptions):
        # Existing initialization
        if options.get('prompt_dir'):
            self.load_prompt_folder(options['prompt_dir'])
    
    def load_prompt_folder(self, dir: str = './prompts'):
        """Load all .prompt files from directory."""
        load_prompt_folder(self.registry, dir)
```

### Phase 5: Testing and Validation

#### 5.1 Unit Tests Structure
```
py/packages/genkit/tests/dotprompt/
├── test_parser.py          # Test YAML parsing and validation
├── test_template.py        # Test template rendering
├── test_loader.py          # Test file loading and caching
├── test_integration.py     # Test ExecutablePrompt integration
├── fixtures/
│   ├── simple.prompt       # Basic test prompt
│   ├── complex.prompt      # Advanced features test
│   └── variant.test.prompt # Variant testing
└── helpers.py              # Test utilities
```

#### 5.2 Test Cases Coverage
- **Parser Tests**: YAML frontmatter parsing, error handling, schema validation
- **Template Tests**: Variable substitution, conditionals, loops, helpers
- **Loader Tests**: Directory scanning, file caching, variant resolution
- **Integration Tests**: End-to-end prompt execution, compatibility with existing API

#### 5.3 Performance Testing
- Template compilation and caching performance
- File loading and scanning benchmarks
- Memory usage with large prompt libraries

### Phase 6: Documentation and Examples

#### 6.1 Documentation Updates
- Add dotprompt section to Python documentation
- Create migration guide from programmatic to file-based prompts
- API reference documentation
- Best practices guide

#### 6.2 Example Implementation
Create sample prompts and usage examples:

```python
# examples/dotprompt_example.py
from genkit import genkit
from genkit.dotprompt import load_prompt_folder

# Initialize with prompt directory
ai = genkit({
    'plugins': [google_genai()],
    'prompt_dir': './prompts'
})

# Use file-based prompt
greeting_prompt = ai.prompt('greeting', variant='formal')
response = await greeting_prompt({'name': 'Alice', 'location': 'hotel lobby'})
```

## Implementation Timeline

### Week 1-2: Foundation
- Set up module structure and dependencies
- Implement basic parser and template engine
- Create initial test framework

### Week 3-4: Core Features
- Complete file loader implementation
- Integrate with ExecutablePrompt class
- Add registry support

### Week 5-6: Advanced Features
- Implement helpers and partials
- Add variant support
- Performance optimization

### Week 7-8: Testing and Polish
- Comprehensive testing suite
- Documentation and examples
- Performance benchmarking

## Risk Assessment and Mitigation

### Technical Risks

1. **Template Engine Compatibility**
   - **Risk**: Python Handlebars libraries may not match JavaScript behavior exactly
   - **Mitigation**: Create compatibility tests with shared .prompt files, implement custom engine if needed

2. **Performance Impact**
   - **Risk**: File scanning and template compilation may slow startup
   - **Mitigation**: Implement intelligent caching, lazy loading, and production optimization

3. **Schema Validation**
   - **Risk**: Python typing system differences from JavaScript schemas
   - **Mitigation**: Create schema translation layer, use Pydantic for validation

### Project Risks

1. **Breaking Changes**
   - **Risk**: Integration might break existing Python code
   - **Mitigation**: Maintain backward compatibility, gradual rollout strategy

2. **Maintenance Overhead**
   - **Risk**: Additional complexity in codebase
   - **Mitigation**: Comprehensive documentation, clear separation of concerns

## Success Criteria

### Functional Requirements
- ✅ Parse .prompt files with YAML frontmatter
- ✅ Process Handlebars-compatible templates
- ✅ Load prompts from directories automatically
- ✅ Support prompt variants and namespaces
- ✅ Maintain backward compatibility with existing API

### Performance Requirements
- Template compilation under 10ms per prompt
- Directory scanning under 100ms for 100 prompts
- Memory usage increase under 10MB for typical usage

### Quality Requirements
- 95%+ test coverage for new code
- Zero breaking changes to existing API
- Documentation coverage for all new features

## Conclusion

This implementation plan provides a comprehensive roadmap for integrating dotprompt functionality into the Python version of Firebase Genkit. The phased approach ensures systematic development while maintaining backward compatibility and code quality.

The integration will significantly enhance the Python implementation's capabilities, bringing it closer to feature parity with the stable JavaScript version and providing developers with a consistent, file-based approach to prompt management across both language implementations.

Key benefits of this implementation:
- **Developer Experience**: File-based prompt management with version control
- **Maintainability**: Separation of prompts from code logic
- **Reusability**: Shared prompts across different parts of applications
- **Collaboration**: Non-technical team members can edit prompts
- **Testing**: Easier prompt testing and validation

The successful completion of this integration will mark a significant milestone in the Python implementation's maturity and adoption potential.

---

**Document Version**: 1.0  
**Date**: January 2025  
**Issue Reference**: [Firebase Genkit #3280](https://github.com/firebase/genkit/issues/3280)
