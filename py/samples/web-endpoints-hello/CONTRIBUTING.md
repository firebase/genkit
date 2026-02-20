# How to Contribute

We'd love to accept your patches and contributions to this project.

## Before you begin

### Sign the Contributor License Agreement

Contributions to this project must be accompanied by a
[Contributor License Agreement](https://cla.developers.google.com/about) (CLA).
You (or your employer) retain the copyright to your contribution; this simply
gives us permission to use and redistribute your contributions as part of the
project.

If you or your current employer have already signed the Google CLA (even if it
was for a different project), you probably don't need to do it again.

Visit <https://cla.developers.google.com/> to see your current agreements or to
sign a new one.

### Review our community guidelines

This project follows
[Google's Open Source Community Guidelines](https://opensource.google/conduct/).

## Development setup

```bash
# Clone the repo and navigate to the sample
git clone https://github.com/firebase/genkit.git
cd genkit/py/samples/web-endpoints-hello

# Install all dependencies (production + dev + test + docs)
uv sync --all-extras

# Run linters and type checkers
just lint

# Run tests
just test
```

## Contribution process

### Code reviews

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult
[GitHub Help](https://help.github.com/articles/about-pull-requests/) for more
information on using pull requests.

### Before sending a PR

1. **Format and lint** your code:

    ```bash
    just fmt
    just lint
    ```

2. **Run the full test suite**:

    ```bash
    just test
    ```

3. **Run security checks** (optional but recommended):

    ```bash
    just security
    ```

4. **Build the docs** to verify your changes render correctly:

    ```bash
    just docs-build
    ```

### Commit style

- Use clear, descriptive commit messages.
- Reference related GitHub issues where applicable.
- Keep commits focused — one logical change per commit.

### Code style

- Follow the project's existing code style (enforced by `ruff`).
- All public functions and classes must have Google-style docstrings.
- Type annotations are required on all function signatures.
- Per-line `# noqa` / `# type: ignore` comments must include the specific
  rule code and a brief explanation.

See [GEMINI.md](GEMINI.md) for the full coding guidelines.
