# Create Pull Request

Create a pull request for the current branch using GitHub CLI.

## Instructions

1. Run `git log main..HEAD --oneline` and `git diff main..HEAD --stat` to understand all changes in the branch.
2. Determine the appropriate PR title:
   - Always start with an emoji icon that reflects the nature of the change
   - Keep it short (under 70 characters including the icon)
   - Icon examples: ✨ new feature, 🐛 bug fix, 📝 docs, 🔧 config/chore, ♻️ refactor, 🚀 deploy, 🎨 style/UI, 🏗️ architecture, 🧹 cleanup
3. Read the PR template from `.github/pull_request_template.md` and fill it in with relevant content.
4. Push the branch if needed, then create the PR using `gh pr create` with `--body-file` or a HEREDOC for the body. Target `main` as the base branch.
5. Do NOT include any Claude Code footers or attribution in the PR body.
6. Return the PR URL when done.
