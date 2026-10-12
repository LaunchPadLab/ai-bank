# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases are automated with [release-please](https://github.com/googleapis/release-please);
entries are generated from [Conventional Commit](https://www.conventionalcommits.org) messages.

## [1.1.0](https://github.com/LaunchPadLab/ai-bank/compare/v1.0.0...v1.1.0) (2026-10-12)


### Features

* add guarded Render remediation workflow ([#15](https://github.com/LaunchPadLab/ai-bank/issues/15)) ([a2e6a43](https://github.com/LaunchPadLab/ai-bank/commit/a2e6a435eebe45ce6b903945a24c29658cdc1276))
* add render-operations skill and render-ops-agent ([#14](https://github.com/LaunchPadLab/ai-bank/issues/14)) ([b8fc069](https://github.com/LaunchPadLab/ai-bank/commit/b8fc069a8031a394d3e723aae3010b247ce54255))


### Documentation

* add Claude Code system prompt customization field guide ([#8](https://github.com/LaunchPadLab/ai-bank/issues/8)) ([0f69e1d](https://github.com/LaunchPadLab/ai-bank/commit/0f69e1d93eb3b882df5e174b8af06a37feaf0fc5))
* add Claude vs OpenAI model/effort selection guide ([#10](https://github.com/LaunchPadLab/ai-bank/issues/10)) ([e99aa4a](https://github.com/LaunchPadLab/ai-bank/commit/e99aa4affbbf75744b58f75cd6fccf563ad438ef))
* add Render infrastructure-agent playbook ([#16](https://github.com/LaunchPadLab/ai-bank/issues/16)) ([3a9a4ad](https://github.com/LaunchPadLab/ai-bank/commit/3a9a4adc5a1a49c56bcfa4a4ba760f35d96b14f4))

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
