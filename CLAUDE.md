# GConfig Python

Legacy Python configuration library used across Gordian Python services. Provides a fallback chain for configuration: environment variables, AWS Secrets Manager, and default values.

## On Session Start

**IMPORTANT:** At the start of each session, follow these steps:

1. Run `whoami` to get the current username
2. Check if `claude_code/<username>/CLAUDE.md` exists
3. If it exists: Read and follow the user's profile
4. If it doesn't exist:
   - List available profiles in `claude_code/` (directories containing CLAUDE.md)
   - Ask the user if they want to:
     a. Create a new profile from the template (`claude_code/templates/user-profile-template.md`)
     b. Copy an existing profile
     c. Continue without a profile

## File Resolution (Override System)

When loading any file from `claude_code/`:
1. **First check:** `claude_code/<username>/<path>` (user override)
2. **Fallback:** `claude_code/<path>` (shared default)

This allows individual customization while maintaining shared baselines.

## Tech Stack

- **Language:** Python
- **Cloud:** AWS Secrets Manager

## Usage

Used by corev1, corev2, content, and other Python services for configuration management.

## MCP Servers

This project includes a `.mcp.json` configuration with the following MCP servers:

### GitHub (`github`)
Provides GitHub integration for PRs, issues, code search, and repository management.
- **Type:** HTTP
- **Setup:** Requires `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable
- **Docs:** https://github.com/github/github-mcp-server

### Linear (`linear`)
Project management integration for issue tracking and sprint planning.
- **Type:** HTTP (OAuth - will prompt for authentication on first use)
- **Docs:** https://linear.app/docs/mcp

### Context7 (`context7`)
Up-to-date documentation lookups for libraries and frameworks.
- **Type:** stdio (via npx)
- **Docs:** https://github.com/upstash/context7

### Setup

MCP servers are configured in `.mcp.json` at the project root. Claude Code will prompt to approve each server on first use. To set up GitHub access:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="your-token-here"
```
