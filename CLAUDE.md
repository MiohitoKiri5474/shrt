# CLAUDE.md

Project-level instructions for Claude Code.

## Branch & Worktree Workflow

### Feature Development

- Branch base: `develop`
- Branch name: `feature/xxx` (where `xxx` is the feature name)
- Worktree directory: `./worktrees/feature-xxx`

```bash
git worktree add ./worktrees/feature-xxx -b feature/xxx develop
```

### Bug Fixes

- Branch base: `develop`
- Branch name: `fix/xxx` (where `xxx` is the fix name)
- Worktree directory: `./worktrees/fix-xxx`

```bash
git worktree add ./worktrees/fix-xxx -b fix/xxx develop
```

### Merge Order

```
feature/xxx or fix/xxx → develop → main
```

**Never commit directly to `main` or `develop`.** All work goes to a feature or fix branch first, then merges into `develop`, then `develop` merges into `main`.
