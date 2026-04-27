---
name: "hotwire-native-path-config"
description: "Configure and debug Hotwire Native path configurations for iOS and Android apps. Use when reviewing path-configuration.json files, adding routing rules for new screens, debugging modal/navigation issues, optimizing pull-to-refresh behavior, or when user mentions path configuration, path rules, or navigation routing in Hotwire Native context."
---

<!-- Codex transposition: omitted Claude-specific frontmatter fields: allowed-tools. -->

# Hotwire Native Path Configuration

Configure URL routing rules that control navigation behavior in Hotwire Native iOS/Android apps.

## Configuration Files in This Project

The paths below are examples from one app layout. Replace them with the current repo's actual remote and bundled path configuration files before editing.

| File | Purpose |
|------|---------|
| `public/configurations/ios_v1.json` | Remote iOS config (fetched from server) |
| `public/configurations/android_v1.json` | Remote Android config (fetched from server) |
| `ios/LifeMuse-iOS/path-configuration.json` | Bundled iOS config (offline fallback) |
| `android/app/src/main/assets/json/configuration.json` | Bundled Android config (offline fallback) |

**Keep bundled and remote configs in sync.** Remote configs allow updates without app releases.

## Quick Reference

### Minimal Config Structure

```json
{
  "settings": {},
  "rules": [
    { "patterns": [".*"], "properties": { "context": "default" } }
  ]
}
```

### Common Rule Patterns

```json
// Modal for /new and /edit paths
{ "patterns": ["/new$", "/edit$"], "properties": { "context": "modal", "pull_to_refresh_enabled": false } }

// Replace navigation (no back button)
{ "patterns": ["/dashboard$"], "properties": { "presentation": "replace" } }

// Hide navigation bar
{ "patterns": ["/auth"], "properties": { "navigation_bar_hidden": true } }
```

### Platform Differences

**Android requires `uri` property** mapping to a registered Fragment:

```json
// iOS
{ "patterns": [".*"], "properties": { "context": "default" } }

// Android (same rule)
{ "patterns": [".*"], "properties": { "context": "default", "uri": "hotwire://fragment/web" } }
```

Common Android URIs:
- `hotwire://fragment/web` — Standard web view
- `hotwire://fragment/web/modal/sheet` — Modal sheet

## Adding a New Screen Rule

1. Identify the URL path pattern (use regex, `$` for end anchor)
2. Determine presentation: `default` (push) or `modal`
3. Set pull-to-refresh: disable for modals/forms
4. Add rule to **all four config files**
5. Android: include appropriate `uri`

## Debugging Checklist

**Screen not showing as modal?**
- Verify `"context": "modal"` in properties
- Check pattern matches the URL (test regex)
- Ensure rule appears after the default `.*` rule

**Pull-to-refresh not working?**
- Check `pull_to_refresh_enabled: true`
- Look for later rules overriding the setting

**Navigation stuck or unexpected?**
- Rules are sequential — later rules override earlier ones
- Check for overlapping patterns

**Android crash on navigation?**
- Verify `uri` property exists and maps to registered Fragment
- Check `HotwireDestinationDeepLink` annotation in Kotlin code

## Reference

See [references/path-configuration.md](references/path-configuration.md) for complete property documentation, modal styles, and advanced patterns.
