# Contributing to Genkit Testapps

Thank you for your interest in contributing to Genkit testapps!

## Before You Begin

Please read the main repository's [CONTRIBUTING.md](../../CONTRIBUTING.md) for general contribution guidelines, including:
- Signing the Contributor License Agreement (CLA)
- Code of Conduct
- Development workflow

## Development Setup

### Prerequisites

- Node.js 22.x or later
- pnpm 10.x or later
- Python 3.10+ (for backend)

### Getting Started

```bash
# Navigate to testapps directory
cd py/testapps

# Install dependencies
pnpm install

# Run tests
pnpm run test

# Run linter
pnpm run check

# Start the chat frontend
cd genkit-chat/frontend && pnpm start

# Start the chat backend (in another terminal)
cd genkit-chat/backend && uv run fastapi dev
```

## Code Standards

### TypeScript/Angular

- **Strict TypeScript**: All code must pass strict type checking
- **Biome**: Code must pass `pnpm run check` (lint + format)
- **Testing**: Add unit tests for new functionality
- **Documentation**: Add JSDoc comments to public APIs

### Python

- **Type hints**: Use type hints for all functions
- **Testing**: Add pytest tests for new functionality
- **Formatting**: Use ruff for formatting

## Pull Request Process

1. **Fork and branch**: Create a feature branch from `main`
2. **Make changes**: Implement your feature or fix
3. **Test locally**: Run `pnpm run test` and `pnpm run check`
4. **Commit**: Use [Conventional Commits](https://www.conventionalcommits.org/)
5. **Push and PR**: Create a pull request to `main`

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Scopes: `testapps`, `genkit-ui`, `genkit-chat`, `frontend`, `backend`

Examples:
```
feat(genkit-ui): add ChatInputComponent with voice support
fix(genkit-chat): resolve SSE connection timeout issue
docs(testapps): update README with setup instructions
```

## Questions?

Open an issue or reach out on the [Firebase Discord](https://discord.gg/firebase).
