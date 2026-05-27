# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases are automated with [release-please](https://github.com/googleapis/release-please);
entries are generated from [Conventional Commit](https://www.conventionalcommits.org) messages.

## [1.0.0] - 2026-05-27

Initial public release of the **ai-bank** catalog and tooling.

### Added

- **Catalog of AI-tooling assets** for Rails/Hotwire development: Claude Code skills,
  agents, commands, and path-scoped rules under `claude/`, with Codex-native (`codex/`)
  and Cursor (`cursor/`) transpilations.
- **Read-only MCP server** (`aibank-mcp`, FastMCP) exposing the catalog over stdio and
  streamable HTTP, with `search`, `list_*`/`get_*`, and `get_rules_for_path` tools, JSON
  resources, and the command set surfaced as MCP prompts.
- **Grounded chat web app** (`aibank-web`, FastAPI) that answers natural-language
  questions strictly from the catalog and cites its sources, reusing the MCP server's
  in-process catalog.
- **Claude Code plugin** (`ai-bank`) and the `launchpadlab` plugin marketplace for
  one-command connection to the hosted MCP server behind Cloudflare Access.
- **Container image and CI**: multi-arch Docker image published to GHCR, plugin-manifest
  validation, and server lint/test workflows.

[1.0.0]: https://github.com/LaunchPadLab/ai-bank/releases/tag/v1.0.0
