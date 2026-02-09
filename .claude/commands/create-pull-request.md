# Create Pull Request

Create a pull request for the current branch using GitHub CLI.

## Instructions

1. Run `git log main..HEAD --oneline` and `git diff main..HEAD --stat` to understand all changes in the branch.
2. Determine the appropriate PR title:
   - Always start with an emoji icon that reflects the nature of the change
   - Keep it short (under 70 characters including the icon)
   - Icon examples: ✨ new feature, 🐛 bug fix, 📝 docs, 🔧 config/chore, ♻️ refactor, 🚀 deploy, 🎨 style/UI, 🏗️ architecture, 🧹 cleanup
3. Write a concise body summarizing the changes.
4. Push the branch if needed, then create the PR:

```bash
gh pr create --title "🔧 Title here" --body "$(cat <<'EOF'
## Summary
- bullet points describing changes

## Test plan
- [ ] testing steps
EOF
)" --base main
```

5. Return the PR URL when done.
