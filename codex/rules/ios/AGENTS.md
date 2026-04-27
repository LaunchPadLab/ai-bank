# Codex Instructions: ios

This AGENTS.md template was transposed from Claude rule files.
Codex applies AGENTS.md instructions to the directory tree containing the file; copy this template into the matching project directory.

## Included Source Rules

- `claude/rules/ios.md`

## Source: `claude/rules/ios.md`

# iOS App (Hotwire Native)

- Treat `ios/` as a native shell around Rails web content.
- Use Swift/UIKit and Hotwire Native conventions already present in the app.
- Discover actual project names, targets, bundle IDs, and path configuration files from the repository before editing.
- Keep local bundled path configuration and remote Rails-served configuration in sync when both exist.
- Register bridge components in the native app and keep their JavaScript counterparts aligned.
- For detailed setup, navigation, authentication, and bridge guidance, defer to the `hotwire-native-ios` and `hotwire-native-auth` skills.
- Run the app's existing `xcodebuild` commands or scheme-specific tests; do not assume a hardcoded scheme name.
