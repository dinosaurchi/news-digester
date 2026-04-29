# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.0   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue in
SME News Admin, please report it responsibly.

**Do not** file a public GitHub issue. Instead, report vulnerabilities privately
by emailing:

> **security@sme-news-admin.dev**

Please include the following in your report:

- A description of the vulnerability and its potential impact
- Steps to reproduce the issue
- Any proof-of-concept code or screenshots
- The version(s) affected
- Your preferred contact information for follow-up

### What to Expect

1. **Acknowledgment** — We will acknowledge your report within **48 hours**.
2. **Triage** — We will assess the severity and confirm the vulnerability
   within 5 business days.
3. **Updates** — We will provide status updates at least every 7 days until
   the issue is resolved.
4. **Resolution** — We aim to deliver a fix within **90 days** of
   confirmation, or provide a mitigation if a full fix requires more time.
5. **Disclosure** — We will coordinate disclosure with you. We kindly request
   that you do not disclose the vulnerability publicly until a fix has been
   released.

### Disclosure Policy

- We practice **coordinated disclosure**. Once a fix is available and released,
  we will publish a security advisory on GitHub.
- We will credit the reporter unless they prefer to remain anonymous.
- We will not take legal action against researchers who report vulnerabilities
  in good faith.

## Security Considerations

### Authentication

Admin credentials are configured through environment variables
(`ADMIN_USERNAME`, `ADMIN_PASSWORD`). Default development credentials (`admin`
/ `admin`) must **never** be used in production or shared deployments. Always
set strong, unique credentials before exposing the application.

### CORS Configuration

The backend's Cross-Origin Resource Sharing (CORS) policy is configured via
environment variables. In production, restrict allowed origins to the exact
frontend domain. Avoid using wildcard (`*`) origins in any non-local
environment.

### Environment Variable Security

- All secrets (database URLs, API keys, credentials, tokens) are managed
  through environment variables.
- Use the provided `.env.example` as a template; never commit actual `.env`
  files or real secrets to the repository.
- The `.gitignore` configuration excludes `.env`, `.secrets/`, and related
  files. Verify that no sensitive files are staged before pushing.

### Dependencies

- Keep all dependencies (npm packages, Python packages, Docker base images)
  up to date to mitigate known vulnerabilities.
- Run `npm audit` and review Python dependency advisories regularly.
- Use pinned versions in production deployments to ensure reproducibility.

## Policy

SME News Admin follows a **responsible disclosure** process:

| Milestone                     | Target              |
| ----------------------------- | ------------------- |
| Acknowledge report            | Within 48 hours     |
| Confirm and triage            | Within 5 business days |
| Provide status updates        | Every 7 days        |
| Deliver fix or mitigation     | Within 90 days      |
| Publish security advisory     | After fix is released |

We appreciate the efforts of security researchers and the community in helping
keep SME News Admin secure.
