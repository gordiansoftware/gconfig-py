# GConfig Python

Legacy Python configuration library used across Gordian Python services. Provides a fallback chain for configuration: environment variables, AWS Secrets Manager, and default values.

## Tech Stack

- **Language:** Python
- **Cloud:** AWS Secrets Manager

## Usage

Used by corev1, corev2, content, and other Python services for configuration management.

## MCP Servers

| MCP | Local/Remote | Purpose |
|-----|-------------|---------|
| `github` | REMOTE | GitHub PRs, issues, code search |
| `linear` | REMOTE | Issue tracking, sprint planning |
| `context7` | LOCAL | Library/framework documentation lookups |
| `aws` | REMOTE | AWS resource inspection (SigV4 authenticated) |

Setup: See root `CLAUDE.md` for environment variable configuration.
