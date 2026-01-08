# LaunchPad Lab AI-BANK

A centralized repository of AI tools, skills, and rules for AI-powered development environments like Cursor and Claude Code.

## Overview

AI-BANK provides reusable configuration files that enable AI agents to follow consistent, domain-specific patterns across projects. These include workflow commands, compliance rules, and development skills that can be imported into any project.

## Directory Structure

```
ai-bank/
├── claude/                      # Claude Code configuration
│   ├── commands/                # Workflow commands (slash commands)
│   └── skills/                  # Domain-specific skills
├── cursor/                      # Cursor IDE configuration
│   └── rules/                   # Context-aware rules with glob patterns
├── resources/                   # Guides and documentation
│   ├── documentation/           # AI usage guides
│   └── mcp/                     # MCP server guides
└── claude-md-templates/         # Reusable markdown templates
```

## What's Included

### Claude Commands (`claude/commands/`)

Workflow commands that can be invoked as slash commands in Claude Code:

| Command | Description |
|---------|-------------|
| `create-prd` | Generate Product Requirements Documents |
| `create-pull-request` | GitHub CLI-based PR creation with templates |
| `pr-review` | Multi-role PR review process |
| `sync-asana` | Sync user stories from markdown to Asana |

### Claude Skills (`claude/skills/`)

Domain-specific knowledge that Claude Code can reference:

| Skill | Description |
|-------|-------------|
| `nova` | Nova project workflow and methodology |
| `hipaa-compliance` | HIPAA compliance rules and patterns |
| `hipaa-infrastructure` | Infrastructure and deployment requirements |
| `hipaa-notifications` | Notification and messaging compliance |
| `hipaa-security` | Security, encryption, and access control |

### Cursor Rules (`cursor/rules/`)

Context-aware rules for Cursor IDE with glob patterns for automatic activation:

| Rule | Description |
|------|-------------|
| `nova` | Nova workflow rules |
| `nova-process` | Nova process guidance |
| `hipaa-compliance` | HIPAA core compliance rules |
| `hipaa-infrastructure` | Infrastructure rules |
| `hipaa-notifications` | Notification rules |
| `hipaa-security` | Security rules |
| `scope-sentinel` | Contract compliance and scope management |

### Resources (`resources/`)

Guides and documentation for AI tooling:

| Directory | Description |
|-----------|-------------|
| `documentation/` | AI usage guidelines and best practices |
| `mcp/guides/` | MCP server setup and security guides |

### Templates (`claude-md-templates/`)

Reusable markdown templates for Claude configuration files.

## Usage

### Cursor

Copy or symlink desired rules to your project's `.cursor/rules/` directory:

```bash
cp -r cursor/rules/hipaa-compliance /path/to/project/.cursor/rules/
```

### Claude Code

Copy or symlink desired skills/commands to your project's `.claude/` directory:

```bash
cp -r claude/skills/hipaa-compliance /path/to/project/.claude/skills/
cp -r claude/commands/pr-review.md /path/to/project/.claude/commands/
```

## Contributing

To add new skills or rules:

1. Create a new directory under the appropriate location (`claude/skills/`, `cursor/rules/`)
2. Add a `SKILL.md` or `RULE.md` file following existing patterns
3. For Cursor rules, include YAML frontmatter with `description`, `globs`, and `alwaysApply` fields
