# Contributing to Genkit Chat

Thank you for your interest in contributing to Genkit Chat! This sample application demonstrates how to build a production-grade chat interface using Firebase Genkit with Python.

## Before You Begin

### Sign the Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License Agreement (CLA). You (or your employer) retain the copyright to your contribution; this simply gives us permission to use and redistribute your contributions as part of the project.

If you or your current employer have already signed the Google CLA (even if it was for a different project), you probably don't need to do it again.

Visit https://cla.developers.google.com/ to see your current agreements on file or to sign a new one.

### Review the Code of Conduct

This project follows the [Google Open Source Community Guidelines](https://opensource.google/conduct/). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How to Contribute

### Reporting Bugs

1. **Check existing issues** - Search the [GitHub issues](https://github.com/firebase/genkit/issues) to see if the bug has already been reported.
2. **Create a new issue** - If not, create a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the problem
   - Expected behavior vs actual behavior
   - Your environment (OS, Python version, Node.js version, browser)
   - Any relevant logs or screenshots

### Suggesting Features

1. Open a [feature request issue](https://github.com/firebase/genkit/issues/new) with the "enhancement" label.
2. Describe the feature and its use case.
3. Explain why this would be useful for other users.

### Submitting Pull Requests

1. **Fork the repository** and create your branch from `main`.
2. **Install dependencies**:
   ```bash
   # Backend
   cd backend
   uv sync
   
   # Frontend
   cd frontend
   pnpm install
   ```
3. **Make your changes** following our coding conventions.
4. **Test your changes**:
   ```bash
   # Backend tests
   cd backend && uv run pytest
   
   # Frontend tests
   cd frontend && pnpm test
   ```
5. **Format your code**:
   ```bash
   # Backend
   cd backend && uv run ruff format .
   
   # Frontend
   cd frontend && pnpm exec ng lint --fix
   ```
6. **Submit a pull request** with a clear title and description.

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- pnpm
- uv (Python package manager)
- Ollama (for local model testing)

### Running Locally

```bash
# Terminal 1: Start backend
cd backend
./run.sh

# Terminal 2: Start frontend
cd frontend
pnpm start
```

### Project Structure

```
genkit-chat/
├── backend/           # Python + Robyn backend
│   ├── src/
│   │   └── main.py   # Routes, Genkit flows
│   └── pyproject.toml
├── frontend/          # Angular 19 frontend
│   ├── src/app/
│   │   ├── core/     # Services
│   │   ├── features/ # Components
│   │   └── shared/   # Pipes, utilities
│   └── package.json
└── README.md
```

## Coding Standards

### Python (Backend)

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and returns
- Write docstrings for public functions and classes
- Keep functions focused and under 50 lines

### TypeScript (Frontend)

- Use Angular's style guide
- Prefer signals over traditional RxJS patterns
- Use strict TypeScript settings
- Write comprehensive type definitions

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(chat): add voice input support
fix(models): handle streaming timeout
docs: update README with setup instructions
test(safety): add toxicity detection tests
```

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
