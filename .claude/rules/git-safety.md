# Git Safety for Multi-Repo Workspace

This repository is part of the Gordian Ancillaries platform — a multi-repo workspace where each service has its own independent git history.

**CRITICAL:** Before any git operation (commit, push, checkout, branch), verify you are in the correct repository directory. Running git commands in the wrong directory is the #1 multi-repo mistake.

- Always check `pwd` before git operations
- Each repo has its own branches, tags, and remotes
- Never commit changes meant for one repo into another
