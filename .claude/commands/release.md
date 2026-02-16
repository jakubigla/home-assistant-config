# Claude Command: Release

Create a GitHub release using CalVer (Calendar Versioning) format.

## CalVer Format

Use the format: `YYYY.MM.PATCH` (e.g., `2026.02.0`, `2026.02.1`)

- `YYYY` — full year
- `MM` — zero-padded month (01–12)
- `PATCH` — zero-based incrementing number within the same month, starting at 0

## Instructions

1. Fetch the latest tags from the remote: `git fetch --tags`
2. List existing tags to determine the next version:
   - Run `git tag --list 'YYYY.MM.*'` using the **current year and month** to find tags for this month.
   - If tags exist for this month, increment the PATCH number (e.g., `2026.02.0` → `2026.02.1`).
   - If no tags exist for this month, start at PATCH `0` (e.g., `2026.02.0`).
3. Determine the previous release tag (the most recent tag before the new one) by running `git tag --sort=-v:refname | head -1`.
4. Generate release notes by examining commits since the previous release:
   - Run `git log <previous_tag>..HEAD --oneline` to get the list of commits.
   - If there is no previous tag, use all commits on `main`.
5. Build release notes in this format:

   ```markdown
   ## What's Changed

   - <commit summary> (<short hash>)
   - <commit summary> (<short hash>)
   ...

   **Full Changelog**: https://github.com/<owner>/<repo>/compare/<previous_tag>...<new_tag>
   ```

   - Group commits logically if there are many (e.g., features, fixes, chores).
   - Strip any `Co-Authored-By` lines from commit messages.
6. Create the release using GitHub CLI:

   ```bash
   gh release create <new_tag> --title "<new_tag>" --notes "$(cat <<'EOF'
   <release notes>
   EOF
   )"
   ```

   - The release targets the current branch (should be `main`).
   - Do NOT mark as pre-release or draft unless the user explicitly asks.
7. Return the release URL when done.

## Important Notes

- Always create the release from the `main` branch. If not on `main`, warn the user and ask for confirmation before proceeding.
- Do NOT include any Claude Code footers or attribution in the release notes.
- If there are no new commits since the last release, inform the user and do not create an empty release.
