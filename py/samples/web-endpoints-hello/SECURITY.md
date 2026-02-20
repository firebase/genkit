# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
responsibly. **Do not open a public GitHub issue.**

Instead, please report vulnerabilities through Google's
[Vulnerability Reward Program](https://bughunters.google.com/about/rules/6625378258649088/google-open-source-software-vulnerability-reward-program-rules)
or by emailing <security@google.com>.

We will acknowledge receipt of your report within 72 hours and aim to provide
a detailed response within one week, including next steps for handling the
vulnerability.

## Supported Versions

This is a sample/template project. Security fixes are applied to the `main`
branch only. We do not maintain backport branches for samples.

## Security Features

This sample includes several built-in security hardening features. See the
[Security documentation](docs/production/security.md) for details:

- OWASP-recommended security headers
- CORS configuration
- Per-IP rate limiting (REST + gRPC)
- Request body size limits
- Input validation via Pydantic field constraints
- Trusted host verification
- Optional Sentry error tracking
- Distroless container image (nonroot)
- Dependency vulnerability scanning (`just audit`)
- License compliance checking (`just licenses`)
