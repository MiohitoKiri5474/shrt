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

### Pull Request Workflow

Pull requests should mention Copilot by using `@copilot` in the description to get AI assistance with code review and suggestions.

Here is the process:

1. Create a pull request from your feature/fix branch to `develop`.
2. Create a comment which mention `@copilot` in the description to get AI review.
3. Wait 15 minutes Copilot's feedback comments. Address the feedback by making necessary changes to your code.
4. Push the changes to your branch and mention `@copilot` again for another review.
5. Repeat steps 2-4 until Copilot approves the pull request.
