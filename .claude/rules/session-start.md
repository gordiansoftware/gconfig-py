# Session Start Protocol

At the start of each session:

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
