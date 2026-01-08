# How to Create a Pull Request Using GitHub CLI

This guide explains how to create pull requests using GitHub CLI in our project.

## Prerequisites

1. Install GitHub CLI if you haven't already:

   ```bash
   # macOS
   brew install gh

   # Windows
   winget install --id GitHub.cli

   # Linux
   # Follow instructions at https://github.com/cli/cli/blob/trunk/docs/install_linux.md
   ```

2. Authenticate with GitHub:
   ```bash
   gh auth login
   ```

## Creating a New Pull Request - Default Method

1. First, prepare your PR description following the template in @.github/PULL_REQUEST_TEMPLATE.md

2. Use the `gh pr create` command to create a new pull request:

   ```bash
   # Basic command structure
   gh pr create --title "type: Your descriptive title" --body "Your PR description" --base dev 
   ```

   For more complex PR descriptions with proper formatting, use the `--body-file` option with the exact PR template structure:

   ```bash
   # Create PR with proper template structure
   gh pr create --title "type: Your descriptive title" --body-file .github/PULL_REQUEST_TEMPLATE.md --base dev
   ```

## Creating a Draft Pull Request

A draft PR should be created only when specified in prompt.

1. First, prepare your PR description following the template in @.github/PULL_REQUEST_TEMPLATE.md

2. Use the `gh pr create --draft` command to create a new pull request:

   ```bash
   # Basic command structure
   gh pr create --draft --title "type: Your descriptive title" --body "Your PR description" --base dev 
   ```

   For more complex PR descriptions with proper formatting, use the `--body-file` option with the exact PR template structure:

   ```bash
   # Create PR with proper template structure
   gh pr create --draft --title "type: Your descriptive title" --body-file .github/PULL_REQUEST_TEMPLATE.md --base dev
   ```

## Best Practices

1. **PR Title Format**: Use conventional commit format

Do not use scopes just type: PR title.

   - Examples:
     - `feature: Add user details endpoint`
     - `bug: Fix login redirect issue`
     - `refactor: Refactor user controller`
2. Use types only from the list below for the PR title:

    chore
    database
    docs
    feature
    fix
    refactor
    revert
    style
    test
    nova 

3. **Description Template**: Always use our PR template structure from @.github/PULL_REQUEST_TEMPLATE.md:

4. **Template Accuracy**: Ensure your PR description precisely follows the template structure:
   - Keep all section headers exactly as they appear in the template
   - Don't add custom sections that aren't in the template

5. **Draft PRs**: Start as draft when the work is in progress
   - Use `--draft` flag in the command
   - Convert to ready for review when complete using `gh pr ready`

### Common Mistakes to Avoid

1. **Incorrect Section Headers**: Always use the exact section headers from the template
2. **Adding Custom Sections**: Stick to the sections defined in the template
3. **Using Outdated Templates**: Always refer to the current @.github/PULL_REQUEST_TEMPLATE.md file

### Missing Sections

Always include all template sections, even if some are marked as "N/A" or "None"

## Additional GitHub CLI PR Commands

Here are some additional useful GitHub CLI commands for managing PRs:

```bash
# List your open pull requests
gh pr list --author "@me"

# Check PR status
gh pr status

# View a specific PR
gh pr view <PR-NUMBER>

# Check out a PR branch locally
gh pr checkout <PR-NUMBER>

# Convert a draft PR to ready for review
gh pr ready <PR-NUMBER>

# Add reviewers to a PR
gh pr edit <PR-NUMBER> --add-reviewer username1,username2

# Merge a PR
gh pr merge <PR-NUMBER> --squash
```

## Using Templates for PR Creation

To simplify PR creation with consistent descriptions, you can create a template file:

1. Create a file named `pr-template.md` with your PR template
2. Use it when creating PRs:

```bash
gh pr create --draft --title "type: Your title" --body-file pr-template.md --base dev
```

## Related Documentation

- [PR Template](.github/pull_request_template.md)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub CLI documentation](https://cli.github.com/manual/)