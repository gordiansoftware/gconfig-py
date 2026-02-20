#!/bin/bash
# Claude Code PreToolUse hook for the Bash tool.
# Intercepts `git commit` commands and checks whether documentation files
# have been staged alongside significant code changes.
#
# Protocol (Claude Code hooks):
#   - Reads JSON from stdin: { "tool_name": "Bash", "tool_input": { "command": "..." }, ... }
#   - To allow: exit 0 (no output needed, or empty stdout)
#   - To block: output JSON with reason to stderr, exit 2
#   - If this script exits non-zero (other than 2) or fails, Claude Code treats it
#     as "allow" by default.

# Intentionally NOT using set -e: we must always handle errors gracefully.

# Trap any unexpected errors to allow through
trap 'exit 0' ERR

# Read the full JSON input from stdin (may be empty)
INPUT=$(cat 2>/dev/null || true)

# If no input, allow through
if [[ -z "${INPUT:-}" ]]; then
    exit 0
fi

# Extract the "command" field from tool_input using python3 for reliable JSON parsing
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tool_input = data.get('tool_input', {})
    if isinstance(tool_input, dict):
        print(tool_input.get('command', ''))
    else:
        print(data.get('command', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

# Check if the command contains a git commit invocation
if ! echo "$COMMAND" | grep -qE '\bgit\s+commit\b'; then
    exit 0
fi

# Check for [docs-ok] bypass in the commit message
if echo "$COMMAND" | grep -qF '[docs-ok]'; then
    exit 0
fi

# Get staged files (Added, Copied, Modified, Renamed, Deleted)
STAGED=$(git diff --cached --name-only --diff-filter=ACMRD 2>/dev/null || true)

# If nothing staged, allow through
if [[ -z "$STAGED" ]]; then
    exit 0
fi

# Check for doc files in staged changes
DOC_FILES=$(echo "$STAGED" | grep -iE '(CLAUDE\.md|README\.md|CHANGELOG\.md|^docs/|^\.claude/(agents|rules|skills)/.*\.md$|^claude_code/)' || true)

# Check for significant code changes (exclude tests, lockfiles, doc files)
CODE_FILES=$(echo "$STAGED" | grep -vE '(test[s]?/|\.test\.|\.spec\.|_test\.|\.lock$|\.sum$|poetry\.lock|yarn\.lock|package-lock\.json|Gemfile\.lock|CLAUDE\.md|README\.md|CHANGELOG\.md|^docs/|^\.claude/(agents|rules|skills)/|^claude_code/)' || true)

# If no significant code files, allow through (doc-only or test-only changes)
if [[ -z "$CODE_FILES" ]]; then
    exit 0
fi

# If doc files are already staged alongside code, allow through
if [[ -n "$DOC_FILES" ]]; then
    exit 0
fi

# Check if changes are only lockfiles (non-significant)
ONLY_LOCKFILES=true
while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    if ! echo "$file" | grep -qE '\.(lock|sum)$|poetry\.lock|yarn\.lock|package-lock\.json|Gemfile\.lock'; then
        ONLY_LOCKFILES=false
        break
    fi
done <<< "$STAGED"

if [[ "$ONLY_LOCKFILES" == "true" ]]; then
    exit 0
fi

# --- Build targeted block message ---

# Get new and deleted files for structural change detection
NEW_FILES=$(git diff --cached --name-only --diff-filter=A 2>/dev/null || true)
DELETED_FILES=$(git diff --cached --name-only --diff-filter=D 2>/dev/null || true)

# Use python3 to analyze changes and build the block reason
REASON=$(python3 -c "
import sys, os, json
from collections import defaultdict

staged = '''$STAGED'''.strip().split('\n') if '''$STAGED'''.strip() else []
new_files = '''$NEW_FILES'''.strip().split('\n') if '''$NEW_FILES'''.strip() else []
deleted_files = '''$DELETED_FILES'''.strip().split('\n') if '''$DELETED_FILES'''.strip() else []

# Categorize changes by directory
dir_counts = defaultdict(int)
for f in staged:
    if not f:
        continue
    parts = f.split('/')
    if len(parts) > 1:
        key = '/'.join(parts[:min(3, len(parts)-1)]) + '/'
    else:
        key = '(root)'
    dir_counts[key] += 1

# Build changed areas description
areas = []
for d, count in sorted(dir_counts.items(), key=lambda x: -x[1]):
    label = ''
    if any(f.startswith(d.rstrip('/') + '/') or f == d.rstrip('/') for f in new_files if f):
        label = ' (new files - Project Structure)'
    elif any(f.startswith(d.rstrip('/') + '/') or f == d.rstrip('/') for f in deleted_files if f):
        label = ' (deleted files - Project Structure)'
    areas.append(f'  - {count} file(s) in {d}{label}')

# Check for package manager / build file changes
pkg_files = [f for f in staged if f and os.path.basename(f) in (
    'package.json', 'pyproject.toml', 'go.mod', 'Gemfile', 'Cargo.toml',
    'Dockerfile', 'Makefile', 'docker-compose.yml', 'docker-compose.yaml'
)]
for pf in pkg_files:
    areas.append(f'  - {pf} modified (Dependencies / Build System)')

# Check for config files at root
root_configs = [f for f in staged if f and '/' not in f and f not in pkg_files
                and not f.endswith('.lock') and not f.endswith('.sum')]
for rc in root_configs:
    areas.append(f'  - {rc} modified (Root Configuration)')

# Build doc review suggestions
docs_to_review = []
docs_to_review.append('  - CLAUDE.md - Check affected sections match current code')

if new_files or deleted_files:
    docs_to_review.append('  - CLAUDE.md Project Structure section - Files added/removed')

if pkg_files:
    docs_to_review.append('  - CLAUDE.md Tech Stack / Dependencies sections')

# Check for agent/rule files that might reference changed areas
agent_dir = '.claude/agents'
if os.path.isdir(agent_dir):
    for agent_file in sorted(os.listdir(agent_dir)):
        if agent_file.endswith('.md'):
            docs_to_review.append(f'  - .claude/agents/{agent_file} - May reference changed code')

msg_lines = [
    'PRE-COMMIT DOCUMENTATION CHECK',
    '',
    'Code changes detected without corresponding documentation updates.',
    '',
    'Changed areas:',
]
msg_lines.extend(areas[:10])  # Cap at 10 to keep message manageable
if len(areas) > 10:
    msg_lines.append(f'  - ... and {len(areas) - 10} more areas')

msg_lines.extend([
    '',
    'Documentation to review:',
])
# Deduplicate doc suggestions
seen = set()
for d in docs_to_review:
    if d not in seen:
        seen.add(d)
        msg_lines.append(d)

msg_lines.extend([
    '',
    'After reviewing:',
    '  1. Update affected docs, stage them, and re-commit',
    '  2. OR if docs are already current, add [docs-ok] to your commit message',
])

print('\n'.join(msg_lines))
" 2>/dev/null || echo "Code changes detected without documentation updates. Review affected docs, stage them, and re-commit. Or add [docs-ok] to your commit message to bypass.")

# Block the commit: output reason to stderr and exit 2
echo "$REASON" >&2
exit 2
