# Security Policy

## Supported Versions

This project follows semantic versioning. During the early open-source phase we
aim to provide security updates for the latest stable release. Older releases
may receive fixes on a best-effort basis.

| Version | Supported          |
| ------- | ------------------ |
| latest  | ✅ Yes             |
| < latest | ⚠️ Best effort    |

## Reporting a Vulnerability

1. **Do not create public issues for security reports.**  
2. Please use GitHub Security Advisories once the repository is published, or
   contact the maintainers via a private channel listed in the project
   documentation.  
3. Include as much detail as possible:
   - Affected components or files
   - Steps to reproduce, including sample payloads
   - Impact assessment (e.g., data exposure, RCE risk)
   - Any suggested remediation or patches

We strive to acknowledge valid reports within **5 working days** and provide a
planned remediation timeline within **10 working days**.

If you have not received a response within the stated time, please send a follow
up via the same private channel.

## Coordinated Disclosure

We appreciate responsible disclosure. Please allow us reasonable time to
investigate, coordinate, and release a fix before any public disclosure.

When a fix is ready, we will:
- Publish a security advisory summarizing the impact, CVSS (if applicable), and
  remediation steps.
- Credit the reporter if they wish to be acknowledged.

## Hardening Best Practices

While we work on official security hardening guides, please consider the
following when deploying:
- Store all API keys and database credentials in your own secrets manager or
  environment variables.
- Configure HTTPS for any public-facing endpoints.
- Rotate credentials regularly and restrict access to necessary resources only.
- Monitor server logs for suspicious activity and enable rate limiting at the
  reverse proxy level.

感谢你的安全守护与贡献！

